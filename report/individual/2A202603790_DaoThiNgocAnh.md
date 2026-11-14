# Báo cáo cá nhân — Day 6

**Học viên:** Đào Thị Ngọc Ánh · **MSSV:** 2A202603790 · **Lớp:** L3B

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:** Sở hữu trí tuệ (Copyright, Trademark, Trade Secret). Nguồn: *Introduction to Intellectual Property* (OpenStax), https://openstax.org/details/books/introduction-intellectual-property, truy cập 2026-11-14. Giấy phép **CC BY 4.0** (trang 4 của PDF ghi *"Textbook content is licensed under a Creative Commons Attribution 4.0 International License"*); sách ghi là chuyển thể từ tài liệu của The Michelson 20MM Foundation. PDF có 201 trang vật lý; tính **38 trang nội dung** (127.083 ký tự) thuộc 3 chương:
  - Chương 3 Copyright: trang PDF 102–103, 114–122 (11 trang).
  - Chương 4 Trademark: 142, 147–157 (12 trang).
  - Chương 5 Trade Secret: 172–186 (15 trang).

  Quy tắc tính trang: chỉ tính trang nội dung chính của các mục đã chọn. Không tính bìa, mục lục, lời nói đầu, trang mở đầu chương chỉ có hình, Assessment Questions, Glossary, Answer Key, Index, và trang chủ yếu là hình (ví dụ 107, 113, 143, 187). Số trang dùng **số thứ tự trang trong file PDF** (ví dụ trang PDF 103 là trang sách 95). Chi tiết ở `data/manifest.json`, được tạo bằng `starter/scripts/build_manifest.py`.
- **Chuẩn hóa, lỗi và giới hạn:** Đọc bằng `pypdf` 7.1.0, chuẩn hóa Unicode NFC, bỏ soft hyphen, nối lại từ bị gạch nối khi xuống dòng, bỏ header/footer lặp lại ("Access for free at openstax.org", dòng số trang) và khối chú thích cuối trang (endnote, bắt đầu bằng số La Mã). Trang dưới 300 ký tự được ghi cảnh báo và bỏ qua. Lần chạy chính thức đọc được 38/38 trang, không có trang lỗi (`starter/results/ingest_log.txt`). Một số hạn chế còn lại:
  - pypdf không giữ dòng trống giữa các đoạn, nên chunking B phải dựa vào heading và ranh giới câu.
  - Chú giải hình (Figure x.y …) và dòng link multimedia vẫn còn trong văn bản.
  - Một số từ có dấu cách thừa sau gạch nối ("non- obviousness").
  - Bước tách câu tạo ra một chunk chỉ dài 1 ký tự (min=1 trong thống kê của B).
- **Embedding và vector store:**
  - Embedding: `intfloat/multilingual-e5-small` chạy local bằng sentence-transformers 6.3.0 (torch 2.15.0+cpu), 384 chiều, vector được chuẩn hóa. Thêm tiền tố `passage: ` cho văn bản tài liệu và `query: ` cho câu hỏi. Giữ nguyên model cho cả 3 cấu hình.
  - Vector store: Chroma 1.5.9 (`PersistentClient`, lưu tại `starter/chroma_db`), metric cosine, tìm kiếm xấp xỉ (HNSW). Đổi từ pgvector sang Chroma vì máy không cài được Docker.
  - Python 3.13.13. Lệnh chạy (tại thư mục `starter/`): `python -m src.run`.
  - Chi phí: **0 USD** (model chạy local).
- **Metadata:** Mỗi chunk có `document_id`, `source`, `page` (bắt buộc), cùng `chapter` (chuỗi "3"/"4"/"5", là trường lọc), `section` và `page_id`. Giá trị `chapter` và `section` lấy từ bookmark của PDF, không tự đoán. Chọn `chapter` làm trường lọc vì nhiều khái niệm xuất hiện ở nhiều chương (đăng ký, bồi thường, fair use), nên biết chương sẽ giúp thu hẹp phạm vi tìm kiếm.

## Cấu hình và benchmark

- **A / B / C:**
  - A: cắt cố định 500 ký tự, chồng lấn 50, không lọc.
  - B: theo cấu trúc, chia khối tại heading rồi gom câu trọn vẹn, tối đa 800 ký tự, không lọc.
  - C: dùng **chính index của B**, chỉ thêm filter `chapter` cho những câu hỏi có filter.

  B và C chỉ khác nhau ở filter; A và B chỉ khác nhau ở cách chunk.
- **Bộ câu hỏi:** 20 câu (`benchmark/questions.json`), chia **15 dev / 5 test**. Các loại câu: direct, paraphrase, conditional, exception, metadata_filter. Có 4 câu filter: q02 (chương 3), q13 (chương 4), q15 (chương 5) thuộc dev, và q20 (chương 5) thuộc test. Câu filter được viết mơ hồ có chủ ý (ví dụ "Khi nào cần đăng ký?"); filter đóng vai trò ngữ cảnh người dùng cung cấp trước khi tìm kiếm. Script `starter/scripts/verify_benchmark.py` xác nhận cả 20 đoạn evidence nằm đúng trang gold; học viên đã mở PDF tự đối chiếu. Câu hỏi do AI soạn nháp, học viên kiểm tra lại. Nguy cơ rò rỉ: dev và test cùng corpus, có thể gần nhau về chủ đề. Tập test lệch về chương 5 (4/5 câu) và không có câu nào của chương 3.
- **Tiêu chí chọn chiến lược:** ưu tiên (1) Evidence Hit@3 trên dev, (2) coherence, (3) tài nguyên (số chunk, thời gian). Kết quả test được tính trong cùng lần chạy với dev, nhưng **không có thay đổi nào về câu hỏi, chia dev/test, tham số chunk hay logic truy xuất sau khi thấy kết quả test** (tác giả xác nhận). Sau lần chạy đầu chỉ sửa 2 chi tiết không ảnh hưởng truy xuất (tắt thanh tiến trình; cách chọn chunk mẫu cho file coherence khi vị trí nằm giữa 2 chunk); chạy lại cho Hit@1/Hit@3 giống hệt.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian embed | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 9/15 | 12/15 | 265 | 13,9 giây | 0 |
| A | test | 4/5 | 4/5 | 265 | | 0 |
| B | dev | 8/15 | 12/15 | 200 | 12,8 giây | 0 |
| B | test | 2/5 | 4/5 | 200 | | 0 |
| C | dev | 8/15 | 13/15 | 200 (index B) | dùng lại index B | 0 |
| C | test | 2/5 | 4/5 | 200 (index B) | | 0 |

Thời gian đọc PDF: 2,9 giây. Kiểm tra nạp lại: số chunk giữ nguyên sau 2 lần upsert (A 265 → 265, B 200 → 200). Độ dài chunk: A có trung vị 500 và trung bình 461,5 ký tự; B có trung vị 646,5 và trung bình 553,9 ký tự.

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1,00 (n=10; điểm 0/1/2 = 0/10/0) | 15/15 | test 1/1* | 0/0/5, trung bình 2,0 |
| B | 1,70 (n=10; điểm 0/1/2 = 0/3/7) | 15/15 | test 1/1* | 0/0/5, trung bình 2,0 |
| C | 1,70 (dùng chunk của B) | 15/15 | dev 3/3, test 1/1 | 0/0/5, trung bình 2,0 |

\* A và B không áp dụng filter. Số 1/1 nghĩa là top-3 của q20 tình cờ đều thuộc chương 5. Ở tập dev, top-3 của A và B tuân thủ filter 0/3.

**Đường dẫn trace, nhãn và cách chọn mẫu:**
- `starter/results/traces_{A,B,C}.jsonl`: câu hỏi, top-3 (id, text, score, metadata), gold, kết quả hit.
- `starter/results/summary.json`: chỉ số tự động, phiên bản thư viện, thống kê chunk.
- `starter/results/manual_coherence.csv`: 10 vị trí cố định, là điểm giữa của 10 trang đầu (sắp theo `pdf_page`), chọn trước khi chấm.
- `starter/results/manual_test_audit.csv`: 5 câu test × 3 cấu hình × top-3.

Nhãn thủ công do AI (Claude) chấm nháp kèm lý do; tác giả đã duyệt lại toàn bộ (coherence 20 nhãn, grounding 15 lượt) và giữ nguyên; cột `labeler` ghi "AI draft (Claude Opus 5.5), reviewed by author". Bảng duyệt rút gọn: `starter/results/REVIEW_grounding.md`. Có nguy cơ thiên lệch vì người chấm cũng là người thiết kế pipeline. Phần kiểm tra metadata dùng script đối chiếu văn bản chunk với trang PDF và chương trong bookmark.

## Phân tích và kết luận

- **So sánh A và B (đổi cách chunk):**
  - Hit@3 trên dev bằng nhau (12/15). Hit@1 dev của A nhỉnh hơn (9 so với 8), và trên test chênh lớn hơn (A 4/5, B 2/5), nhưng mẫu chỉ có 5 câu nên không đủ để kết luận.
  - Coherence của B cao hơn rõ rệt (1,7 so với 1,0): các chunk của A luôn bắt đầu hoặc kết thúc giữa câu, thậm chí giữa từ (ví dụ *"securing for l"*).
  - Lỗi đặc trưng của A là evidence bị cắt ngang giữa 2 chunk: q08, q15 và q20 tìm đúng trang nhưng không chunk nào chứa trọn evidence. B có 200 chunk so với 265 của A, embed nhanh hơn một chút.
- **So sánh B và C (chỉ thêm filter):** C hơn B một câu ở Hit@3 dev (13 so với 12) nhờ câu q02.
- **Ví dụ sai 1 (q02, dev, cần chương 3, gold trang 103):** câu hỏi "Under what condition is registration required?" là câu mơ hồ. A trả về trang 118, 157 (chương 4, đăng ký trademark), 118; B trả về 118, 147 (chương 4), 118. C lọc `chapter=3` nên trả về 118, 118, **103** và có hit ở rank 3. Đây là ví dụ cho thấy metadata giúp loại bỏ đoạn cùng chủ đề nhưng khác chương.
- **Ví dụ sai 2 (q09, dev, gold trang 147, "two primary types of marks"):** cả B và C trả về trang 157, 155, 150. Các chunk này nói về đăng ký và các loại nội dung được bảo hộ, chứa nhiều từ "trademark" nhưng không nêu "trademarks and service marks". Filter không cứu được câu này vì các đoạn sai cùng chương với gold. A cũng trượt top-1 (trang 157) nhưng có hit ở rank 3.
- **Ví dụ sai 3 (q11, dev, gold trang 153):** B tìm đúng trang nhưng evidence bị chia sang 2 chunk do giới hạn 800 ký tự. Định nghĩa Hit tính theo một chunk chứa trọn evidence nên câu này bị tính là miss.
- **Chiến lược chọn: C** theo tiêu chí đã định (Hit@3 dev cao nhất 13/15, coherence 1,7 bằng B, cùng tài nguyên với B).
  - Đánh đổi: filter chỉ có tác dụng khi người dùng hoặc ngữ cảnh cung cấp đúng chương. Nếu filter sai, kết quả sẽ tệ hơn không lọc.
  - Phù hợp khi: corpus có nhiều phạm vi phân biệt rõ và có ngữ cảnh đáng tin.
- **Hạn chế:**
  - Tập test chỉ 5 câu và quá dễ: grounding đạt 2/2 ở mọi cấu hình nên không phân biệt được cấu hình.
  - Tập test lệch về chương 5.
  - Chỉ có một người chấm, có hỗ trợ của AI.
  - Trường `section` là metadata mức trang, không phải mức chunk.
  - Thời gian đo trên một máy và một lần chạy, tìm kiếm HNSW xấp xỉ.
  - Kết luận chỉ áp dụng cho corpus này.
- **Nếu làm lại:**
  - Tách đoạn tốt hơn, dùng layout hoặc khoảng cách dòng để phát hiện đoạn văn.
  - Cho chunk B chồng lấn 1 câu để tránh cắt evidence.
  - Gán `section` theo từng chunk.
  - Làm tập test lớn hơn, cân bằng giữa các chương, có thêm câu khó.
  - Thử hybrid BM25 + dense trên dev.

