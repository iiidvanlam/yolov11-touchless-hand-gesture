"""
Tạo Báo cáo Cuối kỳ / Khóa luận Tốt nghiệp chuyên sâu (30-35+ trang)
Tuân thủ 100% mẫu báo cáo môn Phương Pháp Nghiên Cứu và Viết Báo Cáo Khoa Học
và Quyết định 309/QĐ-ĐHNCT của Trường Đại học Nam Cần Thơ.
"""

import os
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn


def create_report():
    doc = docx.Document()

    def apply_section_margins(section):
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(3.5)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.header_distance = Cm(1.0)
        section.footer_distance = Cm(1.0)

    apply_section_margins(doc.sections[0])

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(13)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.25
    normal_style.paragraph_format.space_before = Pt(6)
    normal_style.paragraph_format.space_after = Pt(0)
    normal_style.paragraph_format.first_line_indent = Cm(1.0)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def add_page_number_to_footer(paragraph):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run()
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0, 0, 0)

        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = "PAGE"
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'separate')
        fldChar3 = OxmlElement('w:fldChar')
        fldChar3.set(qn('w:fldCharType'), 'end')

        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)
        run._r.append(fldChar3)

    def set_section_numbering_type(section, num_fmt='decimal', start_num=1):
        sectPr = section._sectPr
        pgNumType = sectPr.find(qn('w:pgNumType'))
        if pgNumType is None:
            pgNumType = OxmlElement('w:pgNumType')
            sectPr.append(pgNumType)
        pgNumType.set(qn('w:fmt'), num_fmt)
        if start_num is not None:
            pgNumType.set(qn('w:start'), str(start_num))

    def add_p(text, bold=False, italic=False, size=13, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              first_indent=1.0, space_before=6, space_after=2, line_spacing=1.25):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.first_line_indent = Cm(first_indent)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = line_spacing
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_formula(formula_text, eq_num=""):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(formula_text)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(13)
        if eq_num:
            r_num = p.add_run(f"        ({eq_num})")
            r_num.bold = True
            r_num.font.name = 'Times New Roman'
            r_num.font.size = Pt(13)
        return p

    def add_chap_header(chap_num, chap_title):
        p1 = doc.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.first_line_indent = Cm(0)
        p1.paragraph_format.space_before = Pt(12)
        p1.paragraph_format.space_after = Pt(4)
        r1 = p1.add_run(f"CHƯƠNG {chap_num}")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(14)

        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.first_line_indent = Cm(0)
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(14)
        r2 = p2.add_run(chap_title.upper())
        r2.bold = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(14)

    def add_h1(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title_text.upper())
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        return p

    def add_h2(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(title_text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        return p

    def add_bullet(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.25
        r_text = p.add_run("- " + text)
        r_text.font.name = 'Times New Roman'
        r_text.font.size = Pt(13)
        return p

    def add_figure(img_path, fig_num_str, fig_caption, source_text="Tác giả thiết kế và tổng hợp, 2026", width_in=5.7):
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.first_line_indent = Cm(0)
            p_img.paragraph_format.space_before = Pt(10)
            p_img.paragraph_format.space_after = Pt(4)
            p_img.add_run().add_picture(img_path, width=Inches(width_in))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.first_line_indent = Cm(0)
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(2)
        r_num = p_cap.add_run(f"Hình {fig_num_str}. {fig_caption}")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(13)

        p_src = doc.add_paragraph()
        p_src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_src.paragraph_format.first_line_indent = Cm(0)
        p_src.paragraph_format.space_before = Pt(0)
        p_src.paragraph_format.space_after = Pt(10)
        r_src = p_src.add_run(f"(Nguồn: {source_text})")
        r_src.italic = True
        r_src.font.name = 'Times New Roman'
        r_src.font.size = Pt(11.5)

    def format_table_cells(table, col_widths, headers, data, align_rights=[], bold_col0=True):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr = table._tbl.tblPr
        tblBorders = parse_xml(
            r'<w:tblBorders %s>'
            r'  <w:top w:val="single" w:sz="6" w:space="0" w:color="444444"/>'
            r'  <w:left w:val="single" w:sz="6" w:space="0" w:color="444444"/>'
            r'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="444444"/>'
            r'  <w:right w:val="single" w:sz="6" w:space="0" w:color="444444"/>'
            r'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
            r'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="888888"/>'
            r'</w:tblBorders>' % nsdecls('w')
        )
        tblPr.append(tblBorders)

        hdr_row = table.rows[0]
        hdr_row._tr.get_or_add_trPr().append(parse_xml(r'<w:tblHeader %s/>' % nsdecls('w')))
        for i, h_text in enumerate(headers):
            cell = hdr_row.cells[i]
            cell.width = Cm(col_widths[i])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            shd = parse_xml(r'<w:shd %s w:fill="F1F5F9"/>' % nsdecls('w'))
            cell._tc.get_or_add_tcPr().append(shd)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.05
            r = p.add_run(h_text)
            r.bold = True
            r.font.name = 'Times New Roman'
            r.font.size = Pt(12)

        for r_idx, row_data in enumerate(data):
            row = table.rows[r_idx + 1]
            for c_idx, val in enumerate(row_data):
                cell = row.cells[c_idx]
                cell.width = Cm(col_widths[c_idx])
                cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
                p = cell.paragraphs[0]
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.line_spacing = 1.08
                if c_idx in align_rights:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(str(val))
                if c_idx == 0 and bold_col0:
                    r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(11.5)

    def add_custom_table(table_num_str, table_caption, headers, data, col_widths, align_rights=[],
                         source_text="Tổng hợp từ tài liệu kỹ thuật và kết quả thực nghiệm năm 2026", bold_col0=True):
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_cap.paragraph_format.first_line_indent = Cm(0)
        p_cap.paragraph_format.space_before = Pt(10)
        p_cap.paragraph_format.space_after = Pt(4)
        r_num = p_cap.add_run(f"Bảng {table_num_str}. {table_caption}")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(13)

        table = doc.add_table(rows=len(data) + 1, cols=len(headers))
        format_table_cells(table, col_widths, headers, data, align_rights, bold_col0=bold_col0)

        p_src = doc.add_paragraph()
        p_src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_src.paragraph_format.first_line_indent = Cm(0)
        p_src.paragraph_format.space_before = Pt(3)
        p_src.paragraph_format.space_after = Pt(10)
        r_src = p_src.add_run(f"(Nguồn: {source_text})")
        r_src.italic = True
        r_src.font.name = 'Times New Roman'
        r_src.font.size = Pt(11.5)

    # =========================================================================
    # SECTION 1: TRANG BÌA (Không đánh số trang)
    # =========================================================================
    sec_cover = doc.sections[0]
    sec_cover.different_first_page_header_footer = True
    sec_cover.header.is_linked_to_previous = False
    sec_cover.footer.is_linked_to_previous = False

    add_p("TRƯỜNG ĐẠI HỌC NAM CẦN THƠ", bold=False, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=6, space_after=2)
    add_p("KHOA CÔNG NGHỆ THÔNG TIN", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=14)

    logo_path = "report_assets/dnc_logo.png"
    if os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.first_line_indent = Cm(0)
        p_logo.paragraph_format.space_before = Pt(4)
        p_logo.paragraph_format.space_after = Pt(14)
        p_logo.add_run().add_picture(logo_path, width=Inches(1.85))

    add_p("ĐINH VĂN LẮM", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=4, space_after=3)
    add_p("MSSV: 235292", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=3)
    add_p("LỚP: DH23TIN06", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=16)

    add_p("ĐỀ TÀI", bold=False, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=4, space_after=6)
    add_p("XÂY DỰNG HỆ THỐNG NHẬN DIỆN NGÔN NGỮ KÝ HIỆU\n(ASL A-Z) VÀ ĐIỀU KHIỂN THIẾT BỊ KHÔNG CHẠM\nBẰNG YOLOV11-POSE VÀ MEDIAPIPE 3D",
          bold=True, size=17, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=2, space_after=6, line_spacing=1.2)
    add_p("(AN OVERVIEW STUDY AND IMPLEMENTATION OF SIGN LANGUAGE RECOGNITION\nAND TOUCHLESS DEVICE CONTROL USING YOLOV11-POSE AND MEDIAPIPE 3D)",
          bold=False, italic=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=20, line_spacing=1.15)

    add_p("BÁO CÁO CUỐI KỲ", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=4, space_after=3)
    add_p("Phương Pháp Nghiên Cứu và Viết Báo Cáo Khoa Học", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=3)
    add_p("Học kỳ I", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=6)

    add_p("GIẢNG VIÊN HƯỚNG DẪN: TS. NGÔ HỒ ANH KHÔI", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=2, space_after=3)
    add_p("NGÀNH: CÔNG NGHỆ THÔNG TIN", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=3)
    add_p("Mã số ngành: 7480201", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=24)

    add_p("Cần Thơ, Tháng 11/2026", bold=False, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=12, space_after=0)

    # =========================================================================
    # SECTION 2: MỤC LỤC, DANH MỤC TỪ VIẾT TẮT, DANH SÁCH BẢNG & HÌNH (i, ii, iii)
    # =========================================================================
    sec_prelim = doc.add_section()
    apply_section_margins(sec_prelim)
    sec_prelim.header.is_linked_to_previous = False
    sec_prelim.footer.is_linked_to_previous = False
    set_section_numbering_type(sec_prelim, num_fmt='lowerRoman', start_num=1)
    add_page_number_to_footer(sec_prelim.footer.paragraphs[0])

    add_p("MỤC LỤC", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=12, space_after=14)

    toc_items = [
        ("DANH MỤC TỪ VIẾT TẮT", "ii", True, 0),
        ("DANH SÁCH BẢNG", "iii", True, 0),
        ("DANH SÁCH HÌNH", "iii", True, 0),
        ("CHƯƠNG 1: GIỚI THIỆU", "1", True, 0),
        ("1.1 Đặt vấn đề nghiên cứu", "1", False, 1),
        ("1.2 Mục tiêu nghiên cứu", "2", False, 1),
        ("1.3 Phạm vi và đối tượng nghiên cứu", "3", False, 1),
        ("1.4 Ý nghĩa khoa học và giá trị thực tiễn", "4", False, 1),
        ("1.5 Phương pháp nghiên cứu và bố cục báo cáo", "5", False, 1),
        ("CHƯƠNG 2: TỔNG QUAN NỀN TẢNG THỊ GIÁC MÁY TÍNH VÀ KIẾN TRÚC NHẬN DIỆN TƯ THẾ BÀN TAY", "6", True, 0),
        ("2.1 Khái niệm và vai trò của ước lượng tư thế bàn tay 21 khớp xương", "6", False, 1),
        ("2.2 Đánh giá các phương pháp và cảm biến nhận diện cử chỉ thương mại", "8", False, 1),
        ("2.3 Các giải pháp và thư viện thị giác máy tính mã nguồn mở", "9", False, 1),
        ("2.4 Tiêu chí so sánh và kiến trúc phân tầng hệ thống Hybrid", "11", False, 1),
        ("CHƯƠNG 3: MÃ NGUỒN, THUẬT TOÁN HỌC SÂU YOLOV11-POSE VÀ BỘ LỌC TÍN HIỆU THÍCH NGHI", "14", True, 0),
        ("3.1 Nguyên lý mạng YOLOv11-Pose và cơ chế hợp nhất MediaPipe 3D", "14", False, 1),
        ("3.2 Các siêu tham số cốt lõi của YOLOv11-Pose và bộ lọc One-Euro Filter", "17", False, 1),
        ("3.3 Thiết lập đường ống (Pipeline) tiền xử lý, chuẩn hóa 42 chiều và huấn luyện", "19", False, 1),
        ("3.4 Chiến lược phân chia dữ liệu, bộ đệm VotingBuffer và giới hạn mô hình", "21", False, 1),
        ("CHƯƠNG 4: TẬP DỮ LIỆU, THỰC NGHIỆM VÀ ĐÁNH GIÁ MÔ HÌNH NHẬN DIỆN CỬ CHỈ", "23", True, 0),
        ("4.1 Tập dữ liệu chuẩn Hand-Keypoints và cơ sở dữ liệu ASL cá nhân hóa", "23", False, 1),
        ("4.2 Trích xuất đặc trưng hình học bất biến tỷ lệ và góc khớp không gian", "25", False, 1),
        ("4.3 Phương pháp đo lường và các chỉ số đánh giá (OKS, mAP, RMSE, MAE, R²)", "27", False, 1),
        ("4.4 Lịch sử chủ đề và các khoảng trống nghiên cứu", "30", False, 1),
        ("CHƯƠNG 5: KẾT LUẬN VÀ KIẾN NGHỊ", "33", True, 0),
        ("5.1 Kết luận", "33", False, 1),
        ("5.2 Hạn chế của nghiên cứu", "34", False, 1),
        ("5.3 Kiến nghị và hướng phát triển tiếp theo", "35", False, 1),
        ("TÀI LIỆU THAM KHẢO", "36", True, 0),
        ("PHỤ LỤC", "38", True, 0),
    ]

    for title, page, is_bld, lvl in toc_items:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(0.8 if lvl > 0 else 0)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(3 if is_bld else 2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        avail_chars = 78 if lvl == 0 else 72
        dots = "." * max(4, avail_chars - len(title) - len(page))
        r = p.add_run(f"{title}{dots}{page}")
        r.bold = is_bld
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12.5)

    # Trang ii: DANH MỤC TỪ VIẾT TẮT
    doc.add_page_break()
    add_p("DANH MỤC TỪ VIẾT TẮT", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=12, space_after=14)

    acr_headers = ["Từ viết tắt", "Tên tiếng Anh đầy đủ", "Ý nghĩa / Tên tiếng Việt"]
    acr_data = [
        ["AI", "Artificial Intelligence", "Trí tuệ nhân tạo"],
        ["AMP", "Automatic Mixed Precision", "Kỹ thuật tính toán độ chính xác hỗn hợp FP16/FP32"],
        ["API", "Application Programming Interface", "Giao diện lập trình ứng dụng"],
        ["ASL", "American Sign Language", "Ngôn ngữ ký hiệu Mỹ (Bảng chữ cái ngón tay A-Z)"],
        ["CIoU", "Complete Intersection over Union", "Hàm mất mát giao trên hợp hoàn chỉnh cho hộp bao"],
        ["CNN", "Convolutional Neural Network", "Mạng nơ-ron tích chập sâu"],
        ["CUDA", "Compute Unified Device Architecture", "Kiến trúc tính toán song song trên GPU NVIDIA"],
        ["DFL", "Distribution Focal Loss", "Hàm mất mát phân phối tiêu điểm tinh chỉnh biên hộp"],
        ["DIP", "Distal Interphalangeal Joint", "Khớp gian đốt ngón tay xa (gần đầu mút ngón tay)"],
        ["FPS", "Frames Per Second", "Số khung hình xử lý và hiển thị trên mỗi giây"],
        ["HCI", "Human-Computer Interaction", "Lĩnh vực tương tác giữa người và máy tính"],
        ["MAE", "Mean Absolute Error", "Sai số tuyệt đối trung bình"],
        ["mAP", "Mean Average Precision", "Độ chính xác trung bình trên toàn tập ngưỡng"],
        ["MCP", "Metacarpophalangeal Joint", "Khớp bàn đốt ngón tay (nối lòng bàn tay và gốc ngón)"],
        ["OKS", "Object Keypoint Similarity", "Độ tương đồng tọa độ điểm mốc khớp xương"],
        ["PIP", "Proximal Interphalangeal Joint", "Khớp gian đốt ngón tay gần (khớp gập chính giữa ngón)"],
        ["PyCAW", "Python Core Audio Windows Library", "Thư viện giao tiếp tầng sâu âm thanh Windows COM"],
        ["RMSE", "Root Mean Square Error", "Căn bậc hai của sai số toàn phương trung bình"],
        ["ROI", "Region of Interest", "Vùng ảnh quan tâm chứa đối tượng bàn tay"],
        ["TTS", "Text-To-Speech", "Công nghệ tổng hợp văn bản thành tiếng nói tự nhiên"],
        ["YOLO", "You Only Look Once", "Kiến trúc mạng phát hiện đối tượng và tư thế một giai đoạn"],
    ]
    tbl_acr = doc.add_table(rows=len(acr_data) + 1, cols=3)
    format_table_cells(tbl_acr, [2.4, 5.8, 7.3], acr_headers, acr_data, [])
    for row in tbl_acr.rows[1:]:
        row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Trang iii: DANH SÁCH BẢNG & DANH SÁCH HÌNH
    doc.add_page_break()
    add_p("DANH SÁCH BẢNG", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=12, space_after=12)
    tables_list = [
        ("Bảng 2.1: So sánh đặc tính các nền tảng nhận diện cử chỉ thương mại và mã nguồn mở", "10"),
        ("Bảng 3.1: Các siêu tham số cốt lõi của mô hình YOLOv11-Pose và bộ lọc One-Euro Filter", "18"),
        ("Bảng 3.2: Quy tắc ánh xạ giải tích hình học 21 khớp sang cử chỉ Touchless và ASL", "20"),
        ("Bảng 4.1: Cấu trúc các trường thuộc tính trong tập dữ liệu Hand-Keypoints và ASL DB", "24"),
        ("Bảng 4.2: Các chỉ số sai số và độ chính xác đánh giá hiệu năng mô hình nhận diện", "28"),
        ("Bảng 4.3: Kết quả thực nghiệm độ chính xác và thời gian trễ trên GPU NVIDIA RTX 4050", "30"),
    ]
    for t_title, t_page in tables_list:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        dots = "." * max(4, 82 - len(t_title) - len(t_page))
        r = p.add_run(f"{t_title}{dots}{t_page}")
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12.5)

    add_p("DANH SÁCH HÌNH", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=18, space_after=12)
    figures_list = [
        ("Hình 2.1: Mô hình topo giải phẫu 21 điểm khớp xương bàn tay (Hand Landmarks)", "7"),
        ("Hình 2.2: Sơ đồ kiến trúc phân tầng 3 lớp hệ thống nhận diện cử chỉ và điều khiển", "12"),
        ("Hình 2.3: Luồng trao đổi dữ liệu khung hình và sự kiện điều khiển đa luồng thời gian thực", "13"),
        ("Hình 3.1: Cơ chế học kết hợp đa mô hình (Hybrid YOLOv11-Pose, MediaPipe 3D và 1€ Filter)", "16"),
        ("Hình 3.2: Quy trình đường ống (Pipeline) 5 bước tiền xử lý, chuẩn hóa 42-D và suy luận", "19"),
        ("Hình 4.1: Đồ thị hội tụ hàm mất mát (Loss) và độ chính xác mAP50, mAP50-95 theo Epoch", "25"),
        ("Hình 4.2: Biểu đồ so sánh quỹ đạo khớp ngón trỏ thực tế và sau lọc One-Euro Filter", "29"),
        ("Hình 4.3: Biểu đồ phân rã thời gian trễ (Latency Breakdown) và đối sánh FPS CPU - GPU", "30"),
        ("Hình 4.4: Giao diện ứng dụng Desktop PyQt6 Modern Dark UI và hộp thoại ASL Guide thực tế", "31"),
    ]
    for f_title, f_page in figures_list:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        dots = "." * max(4, 82 - len(f_title) - len(f_page))
        r = p.add_run(f"{f_title}{dots}{f_page}")
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12.5)

    # =========================================================================
    # SECTION 3: NỘI DUNG CHÍNH (Đánh số trang Á-rập 1, 2, 3...)
    # =========================================================================
    sec_main = doc.add_section()
    apply_section_margins(sec_main)
    sec_main.header.is_linked_to_previous = False
    sec_main.footer.is_linked_to_previous = False
    set_section_numbering_type(sec_main, num_fmt='decimal', start_num=1)
    add_page_number_to_footer(sec_main.footer.paragraphs[0])

    # -------------------------------------------------------------------------
    # CHƯƠNG 1: GIỚI THIỆU
    # -------------------------------------------------------------------------
    add_chap_header(1, "GIỚI THIỆU")

    add_h1("1.1 ĐẶT VẤN ĐỀ NGHIÊN CỨU")
    add_p("Sự giao thoa giữa Thị giác máy tính (Computer Vision) và Tương tác người - máy (Human-Computer Interaction - HCI) đang tạo ra những thay đổi sâu sắc trong cách thức con người giao tiếp với hệ thống tính toán hiện đại. Các thiết bị ngoại vi tiếp xúc vật lý như bàn phím cơ học, chuột quang học hay màn hình cảm ứng điện dung mặc dù đã định hình tiêu chuẩn nhập liệu trong nhiều thập kỷ nhưng ngày càng bộc lộ rõ giới hạn khi đối diện với các bối cảnh ứng dụng đặc thù. Trong môi trường y tế vô trùng, phòng phẫu thuật ngoại khoa, phòng thí nghiệm sinh học phân tử hoặc các dây chuyền lắp ráp bán dẫn độ sạch cao, việc chạm tay trực tiếp vào bề mặt thiết bị điều khiển làm gia tăng nguy cơ lây nhiễm chéo vi sinh vật và phá vỡ quy trình kiểm soát vô khuẩn. Song song đó, đối với cộng đồng người khiếm thính và khiếm ngôn, rào cản giao tiếp bằng bảng chữ cái ngón tay ngôn ngữ ký hiệu (American Sign Language Fingerspelling - ASL A-Z) với những người xung quanh chưa qua đào tạo chuyên môn vẫn là một thách thức xã hội lớn, đòi hỏi các công cụ dịch thuật tự động theo thời gian thực ngay trên máy tính cá nhân (Zhang et al., 2020).")
    add_p("Để hiểu đầy đủ nội dung nghiên cứu của đề tài, trước hết cần xác định thống nhất các thuật ngữ và khái niệm chuyên ngành làm cơ sở diễn giải những luận điểm kỹ thuật xuyên suốt báo cáo. Khái niệm thứ nhất là bài toán ước lượng tư thế bàn tay hai chiều và ba chiều (2D/3D Hand Pose Estimation), tức quá trình tái tạo cấu trúc khung xương giải phẫu bàn tay thông qua tọa độ của 21 điểm mốc khớp xương (Keypoints/Landmarks) từ luồng hình ảnh RGB thu nhận qua cảm biến quang học thông thường (Simon et al., 2017). Khái niệm thứ hai, giữ vai trò động cơ phát hiện trung tâm của hệ thống, là kiến trúc mạng nơ-ron tích chập một giai đoạn YOLOv11-Pose (You Only Look Once version 11 for Pose Estimation). Đây là mô hình học sâu có giám sát kết hợp khả năng định vị hộp bao đối tượng (Bounding Box Regression) với nhánh hồi quy trực tiếp tọa độ các điểm khớp xương trên nền tảng tăng tốc phần cứng GPU CUDA (Jocher, Qiu, & Chaurasia, 2024). Khái niệm thứ ba là bộ lọc thông thấp tốc độ thích nghi One-Euro Filter (1€ Filter), một giải thuật xử lý tín hiệu số điều chỉnh linh hoạt tần số cắt dựa trên đạo hàm bậc nhất của vị trí theo thời gian nhằm triệt tiêu hiện tượng rung nhiễu cảm biến (Jitter) mà không gây ra độ trễ pha (Lag) khi bàn tay chuyển động nhanh (Casiez, Roussel, & Vogel, 2012).")
    add_p("Tại Việt Nam cũng như trên thế giới, việc triển khai một hệ thống nhận diện cử chỉ bàn tay hoạt động ổn định trong thời gian thực (tốc độ đạt trên 30 khung hình/giây - FPS) trên máy tính phổ thông vẫn gặp phải ba bài toán kỹ thuật cốt lõi. Thứ nhất, bàn tay con người có tới 27 bậc tự do cơ học (Degrees of Freedom - DoF), thường xuyên xảy ra hiện tượng các ngón tay tự che khuất lẫn nhau (Self-occlusion) khi nắm đấm hoặc xoay nghiêng trước ống kính camera một góc hẹp. Thứ hai, các mô hình phát hiện một giai đoạn thuần túy như YOLO tuy có tốc độ quét toàn cảnh rất nhanh nhưng dễ gặp sai số cục bộ ở đốt ngón xa (DIP/TIP), trong khi các mô hình tinh chỉnh đồ thị cục bộ như MediaPipe Hands lại suy giảm hiệu năng khi bàn tay ở cự ly xa hoặc di chuyển đột ngột ra ngoài vùng theo dõi trước đó (Lugaresi et al., 2019). Thứ ba, khi ứng dụng vào dịch thuật ký hiệu chữ cái ASL liên tục hoặc điều khiển âm lượng máy tính không chạm, sự biến thiên góc nhìn giữa các khung hình liên tiếp rất dễ dẫn đến hiện tượng nhảy ký tự rác (Spurious Character Flickering) hoặc kích hoạt nhầm lệnh điều khiển hệ điều hành. Do đó, việc nghiên cứu thiết kế kiến trúc kết hợp (Hybrid Pipeline) giữa sức mạnh định vị toàn cục trên GPU của YOLOv11-Pose, độ chính xác sub-pixel 3D của MediaPipe và cơ chế lọc ổn định chuỗi thời gian One-Euro Filter kết hợp bộ đệm bỏ phiếu xác suất (VotingBuffer) mang ý nghĩa khoa học và giá trị thực tiễn hết sức cấp thiết.")

    add_h1("1.2 MỤC TIÊU NGHIÊN CỨU")
    add_h2("1.2.1 Mục tiêu tổng quát")
    add_p("Mục tiêu tổng quát của đề tài là nghiên cứu cơ sở lý thuyết, phương pháp luận học sâu và xây dựng hoàn chỉnh hệ thống phần mềm Desktop thời gian thực kết hợp kiến trúc mạng YOLOv11-Pose trên GPU NVIDIA CUDA với mô hình tinh chỉnh không gian MediaPipe 3D và bộ lọc tín hiệu thích nghi One-Euro Filter, nhằm giải quyết đồng thời hai bài toán ứng dụng: nhận diện dịch thuật bảng chữ cái ngôn ngữ ký hiệu (ASL A-Z) tích hợp gợi ý từ thông minh cùng phát âm giọng nói (Text-To-Speech), và điều khiển thiết bị máy tính Windows không chạm (Touchless Control) với độ chính xác cao, độ trễ thấp.")

    add_h2("1.2.2 Mục tiêu cụ thể")
    add_p("Để đạt được mục tiêu tổng quát nêu trên, đề tài xác định các mục tiêu nghiên cứu cụ thể sau đây:")
    add_bullet("Khảo sát, phân tích và đối sánh các phương pháp ước lượng tư thế bàn tay từ thiết bị cảm biến phần cứng chuyên dụng (Data Glove, Intel RealSense, Leap Motion) đến các kiến trúc thị giác máy tính mã nguồn mở hiện đại (OpenPose, MediaPipe Hands, YOLOv8-Pose, YOLOv11-Pose) theo các tiêu chí độ chính xác, chi phí triển khai và thông lượng tính toán.")
    add_bullet("Nghiên cứu nguyên lý hoạt động của mạng tích chập YOLOv11-Pose (khối trích xuất C3k2, cơ chế chú ý không gian C2PSA, hàm mất mát OKS/CIoU/DFL) và thiết kế kiến trúc hợp nhất hai giai đoạn (Two-Stage Hybrid Architecture) kết hợp vùng quan tâm mở rộng (ROI Padding 45%) với bộ tinh chỉnh MediaPipe 3D HandLandmarker.")
    add_bullet("Xây dựng hệ thống giải tích hình học bất biến tỷ lệ 42 chiều (Scale-Invariant 42-D Feature Vector), thuật toán hiệu chỉnh giải phẫu đốt ngón xa (Anatomical Tip Correction) và cơ chế phân loại hợp nhất giữa hình học góc khớp (PIP/DIP Angle) với kho mẫu cá nhân hóa k-NN (`asl_keypoints_db.npz`).")
    add_bullet("Thiết lập hệ thống lọc khử nhiễu hai tầng gồm bộ lọc thông thấp thích nghi One-Euro Filter cho tọa độ liên tục và bộ đệm bỏ phiếu cửa sổ trượt (Sliding Window VotingBuffer) kèm bộ đếm chống lặp lệnh (CommandCooldown) nhằm loại bỏ hoàn toàn hiện tượng rung con trỏ và nhảy chữ ASL.")
    add_bullet("Thiết kế và lập trình ứng dụng Desktop đa luồng trên nền tảng PyQt6 (Modern Dark UI), tích hợp giao tiếp tầng sâu hệ điều hành Windows qua Core Audio APIs (PyCAW) để điều khiển âm lượng liên tục bằng khoảng cách chụm ngón (Pinch-to-Volume), phím đa phương tiện Win32 SendInput và bộ đọc giọng nói `pyttsx3`, đồng thời đánh giá thực nghiệm trên GPU NVIDIA GeForce RTX 4050.")

    add_h1("1.3 PHẠM VI VÀ ĐỐI TƯỢNG NGHIÊN CỨU")
    add_h2("1.3.1 Phạm vi nghiên cứu")
    add_p("Một cách tiếp cận chặt chẽ để xác định bài toán thị giác máy tính thời gian thực là phân định rõ không gian trạng thái cử chỉ, điều kiện thu nhận hình ảnh và giới hạn phần cứng triển khai. Về mặt nội dung nhận diện, phạm vi nghiên cứu của đề tài tập trung vào hai nhóm tác vụ chính trên một bàn tay ưu tiên (Dominant Hand) xuất hiện trong khung hình Webcam tiêu chuẩn: thứ nhất là nhận diện tĩnh và bán động toàn bộ 26 chữ cái trong bảng chữ cái ngón tay ngôn ngữ ký hiệu quốc tế (ASL từ A đến Z) cùng hai lệnh soạn thảo trực tiếp là dấu cách (`SPACE`) và xóa ký tự (`DEL`); thứ hai là nhận diện 7 chế độ điều khiển hệ thống không chạm gồm kéo âm lượng liên tục (`PINCH_VOLUME` từ 0% đến 100%), phát/tạm dừng đa phương tiện (`OPEN_PALM`), tắt/bật âm thanh (`FIST`), tăng/giảm âm lượng theo nấc (`THUMBS_UP` / `THUMBS_DOWN`), chuyển bài kế tiếp/lùi bài (`POINT_RIGHT` / `POINT_LEFT`) và chụp ảnh màn hình tức thời (`PEACE`).")
    add_p("Về phạm vi kỹ thuật và môi trường vận hành, hệ thống được nghiên cứu và tối ưu hóa cho luồng video thu nhận từ camera phổ thông độ phân giải HD/Full HD ở tốc độ 30–60 FPS trong điều kiện ánh sáng văn phòng hoặc phòng học trong nhà, với khoảng cách từ bàn tay tới ống kính từ 0,3 m đến 1,5 m. Quá trình huấn luyện và suy luận học sâu được thực nghiệm trên nền tảng hệ điều hành Microsoft Windows 11 64-bit trang bị bộ xử lý đồ họa rời NVIDIA GeForce RTX 4050 Laptop GPU (6 GB GDDR6 VRAM, kiến trúc Ada Lovelace hỗ trợ nhân Tensor Cores thế hệ thứ 4), đồng thời hỗ trợ cơ chế tự động chuyển đổi dự phòng (Fallback) về CPU thông qua định dạng mô hình nhẹ khi chạy trên các máy tính không có card đồ họa rời.")

    add_h2("1.3.2 Đối tượng nghiên cứu")
    add_p("Đối tượng nghiên cứu chính của đề tài bao gồm bốn hợp phần khoa học và công nghệ gắn kết chặt chẽ: (1) Cấu trúc hình học topo 21 điểm mốc giải phẫu khớp xương bàn tay người và các ràng buộc cơ sinh học của chuỗi khớp ngón tay (CMC, MCP, PIP, DIP, TIP); (2) Kiến trúc mạng học sâu ước lượng tư thế YOLOv11-Pose của Ultralytics và mạng tinh chỉnh tọa độ không gian ba chiều MediaPipe HandLandmarker & GestureRecognizer của Google; (3) Các thuật toán xử lý tín hiệu số thời gian thực phục vụ tương tác người - máy, trọng tâm là bộ lọc thích ứng tốc độ One-Euro Filter, trung bình trượt hàm mũ (Exponential Moving Average - EMA) và hàng đợi bỏ phiếu đa khung hình (VotingBuffer); (4) Kiến trúc lập trình phần mềm đa luồng bất đồng bộ trên PyQt6 cùng các giao thức điều khiển hệ thống tầng thấp của Windows (COM `IAudioEndpointVolume` và `SendInput` Virtual-Key Codes).")

    add_h1("1.4 Ý NGHĨA KHOA HỌC VÀ GIÁ TRỊ THỰC TIỄN")
    add_p("Về mặt khoa học, đề tài góp phần hệ thống hóa cơ sở lý thuyết và chứng minh tính hiệu quả của phương pháp kết hợp đa mô hình (Hybrid Multi-Stage Perception) trong bài toán ước lượng tư thế đối tượng có cấu trúc khớp phức tạp. Thay vì phụ thuộc đơn lẻ vào một mạng phát hiện toàn cục hay một mô hình hồi quy cục bộ, nghiên cứu làm rõ cơ chế phối hợp giữa khả năng định vị hộp bao bất biến tỷ lệ của YOLOv11-Pose và khả năng nội suy tọa độ 3D sub-pixel của MediaPipe trên vùng ảnh cắt mở rộng (ROI Padding). Đặc biệt, đề tài đề xuất công thức hiệu chỉnh giải phẫu tự động cho các điểm đầu mút ngón tay bị gập ngược do sai số lượng tử hóa bản đồ nhiệt, kết hợp cùng hệ quy chiếu chuẩn hóa 42 chiều gốc cổ tay, giúp nâng cao đáng kể khả năng phân tách các tư thế bàn tay có hình thái gần trùng nhau trong không gian đặc trưng.")
    add_p("Về mặt thực tiễn, kết quả nghiên cứu cung cấp một sản phẩm phần mềm hoàn chỉnh, mã nguồn mở, có khả năng triển khai ngay trên máy tính cá nhân thông thường mà không đòi hỏi chi phí đầu tư thiết bị cảm biến chiều sâu đắt đỏ. Đối với lĩnh vực công nghệ hỗ trợ người yếu thế (Assistive Technology), ứng dụng đóng vai trò như một cầu nối giao tiếp hai chiều trực quan, hỗ trợ người khiếm thính ghép vần, gợi ý từ vựng tiếng Anh nhanh chóng và phát âm thành tiếng nói rõ ràng. Đối với người dùng máy tính phổ thông, giảng viên thuyết trình hoặc kỹ thuật viên phòng sạch, chế độ điều khiển không chạm cung cấp phương thức tương tác rảnh tay hiện đại, an toàn và mượt mà.")

    add_h1("1.5 PHƯƠNG PHÁP NGHIÊN CỨU VÀ BỐ CỤC BÁO CÁO")
    add_p("Báo cáo sử dụng phương pháp nghiên cứu kết hợp giữa phân tích lý thuyết định lượng, thiết kế kiến trúc phần mềm thực nghiệm và kiểm định thống kê trên tập dữ liệu chuẩn quốc tế lẫn dữ liệu thu thập thực tế. Quy trình nghiên cứu được tổ chức xoay quanh vòng đời phát triển của một hệ thống trí tuệ nhân tạo thời gian thực: khảo sát tổng quan tài liệu nhằm xác định khoảng trống nghiên cứu; xây dựng mô hình toán học cho bài toán ước lượng 21 khớp xương và lọc tín hiệu; thiết lập đường ống huấn luyện mô hình YOLOv11-Pose với kỹ thuật độ chính xác hỗn hợp (AMP FP16) trên GPU; lập trình tích hợp các phân hệ điều khiển hệ điều hành và giao diện người dùng; cuối cùng là đo đạc thực nghiệm độ trễ từng công đoạn (Latency Breakdown), độ chính xác mAP50/mAP50-95 và sai số quỹ đạo RMSE/MAE.")
    add_p("Bố cục bài báo cáo được thiết kế theo trình tự logic chặt chẽ gồm 5 chương chính. Chương 1 trình bày bối cảnh cấp thiết của đề tài, mục tiêu nghiên cứu, phạm vi, đối tượng và phương pháp luận. Chương 2 đi sâu phân tích tổng quan nền tảng thị giác máy tính, đối sánh các công nghệ nhận diện cử chỉ thương mại và mã nguồn mở, từ đó đề xuất kiến trúc phân tầng hệ thống Hybrid. Chương 3 giải trình chi tiết mã nguồn, thuật toán học sâu YOLOv11-Pose, cơ chế hợp nhất MediaPipe 3D, toán học bộ lọc One-Euro Filter và quy trình đường ống xử lý 5 giai đoạn. Chương 4 trình bày chi tiết cấu trúc tập dữ liệu Hand-Keypoints, kỹ thuật trích xuất đặc trưng hình học, kết quả thực nghiệm định lượng cùng phần tổng thuật lịch sử chủ đề và các khoảng trống nghiên cứu. Cuối cùng, Chương 5 tổng kết những đóng góp chính, chỉ rõ hạn chế khách quan của mô hình và đề xuất lộ trình phát triển tiếp theo.")

    # -------------------------------------------------------------------------
    # CHƯƠNG 2: TỔNG QUAN NỀN TẢNG THỊ GIÁC MÁY TÍNH VÀ KIẾN TRÚC NHẬN DIỆN TƯ THẾ BÀN TAY
    # -------------------------------------------------------------------------
    doc.add_page_break()
    add_chap_header(2, "TỔNG QUAN NỀN TẢNG THỊ GIÁC MÁY TÍNH VÀ KIẾN TRÚC NHẬN DIỆN TƯ THẾ BÀN TAY")

    add_h1("2.1 KHÁI NIỆM VÀ VAI TRÒ CỦA ƯỚC LƯỢNG TƯ THẾ BÀN TAY 21 KHỚP XƯƠNG")
    add_p("Ước lượng tư thế bàn tay (Hand Pose Estimation) là một phân nhánh chuyên sâu của thị giác máy tính nhằm mục đích khôi phục cấu hình không gian của bàn tay người từ dữ liệu hình ảnh đầu vào. Khác với bài toán phát hiện bàn tay đơn thuần (Hand Detection) chỉ dừng lại ở việc khoanh vùng một hình chữ nhật bao quanh bàn tay (Bounding Box), hay bài toán phân loại cử chỉ tĩnh (Holistic Gesture Classification) chỉ gán một nhãn duy nhất cho toàn bộ bức ảnh cắt, ước lượng tư thế khớp xương đi sâu giải quyết bài toán định vị chính xác tọa độ của từng khớp giải phẫu cấu thành nên bàn tay (Zimmermann & Brox, 2017). Nhờ biểu diễn bàn tay dưới dạng một đồ thị khung xương có hướng (Directed Kinematic Skeleton Graph), hệ thống có thể suy diễn đồng thời cả vị trí tổng thể, hướng xoay của lòng bàn tay lẫn trạng thái co duỗi tinh vi của từng đốt ngón tay.")
    add_p("Theo quy chuẩn giải phẫu học và tiêu chuẩn hóa dữ liệu trong các tập dữ liệu lớn như CMU Panoptic HandDB (Simon et al., 2017) và MediaPipe Hands (Zhang et al., 2020), cấu trúc bàn tay người được mô hình hóa thông qua đúng 21 điểm mốc khớp xương (21 Keypoints/Landmarks), đánh số thứ tự từ 0 đến 20. Điểm mốc số 0 đại diện cho khớp cổ tay trung tâm (`WRIST`), đóng vai trò là gốc tọa độ cơ sở (Root Node) của toàn bộ cây động học bàn tay. Từ gốc cổ tay này, 5 nhánh chuỗi động học (Kinematic Chains) tỏa ra tương ứng với 5 ngón tay, mỗi ngón tay bao gồm 4 điểm mốc liên tiếp: ngón cái (`THUMB`, các điểm 1, 2, 3, 4 tương ứng khớp CMC, MCP, IP, TIP); ngón trỏ (`INDEX`, các điểm 5, 6, 7, 8 tương ứng khớp MCP, PIP, DIP, TIP); ngón giữa (`MIDDLE`, các điểm 9, 10, 11, 12); ngón áp út (`RING`, các điểm 13, 14, 15, 16) và ngón út (`PINKY`, các điểm 17, 18, 19, 20). Bên cạnh các liên kết dọc theo từng ngón tay, các liên kết ngang nối giữa các khớp bàn đốt (5–9, 9–13, 13–17) tạo thành khung cứng của lòng bàn tay (Palm Rigidity Structure), giúp duy trì tính toàn vẹn hình học khi bàn tay vận động trong không gian ba chiều.")

    add_figure("report_assets/fig_hand_topology.png", "2.1",
               "Mô hình topo giải phẫu 21 điểm khớp xương bàn tay (Hand Landmarks)",
               "Tác giả tổng hợp theo quy chuẩn MediaPipe & Ultralytics, 2026", width_in=3.8)

    add_p("Trong lĩnh vực tương tác người - máy hiện đại, biểu diễn khung xương 21 điểm mốc giữ vai trò nền tảng không thể thay thế. Thứ nhất, việc rút gọn một vùng ảnh bàn tay gồm hàng trăm nghìn điểm ảnh (ví dụ vùng ảnh 300x300x3 = 270.000 giá trị màu) về một ma trận tọa độ kích thước 21x3 (gồm tọa độ x, y và độ tin cậy hoặc độ sâu z) giúp giảm chiều dữ liệu xuống hơn 4.000 lần, cho phép các thuật toán phân loại hậu kỳ thực thi chỉ trong vài phần mười mili-giây. Thứ hai, biểu diễn khung xương hoàn toàn tách biệt khỏi màu sắc da, trang phục hay phông nền phức tạp phía sau người dùng, tạo tiền đề vững chắc để thiết kế các bộ điều khiển không chạm và bộ dịch ngôn ngữ ký hiệu có tính khái quát hóa cao.")

    add_h1("2.2 ĐÁNH GIÁ CÁC PHƯƠNG PHÁP VÀ CẢM BIẾN NHẬN DIỆN CỬ CHỈ THƯƠNG MẠI")
    add_p("Trước khi các mạng nơ-ron học sâu trên camera RGB phổ thông đạt tới độ chín muồi công nghệ, thị trường nhận diện cử chỉ và theo dõi bàn tay chủ yếu dựa vào hai nhóm giải pháp phần cứng chuyên dụng: thiết bị đeo cơ điện tử (Wearable Data Gloves) và cảm biến quang học chiều sâu chuyên biệt (Dedicated Depth & Infrared Sensors). Nhóm thiết bị găng tay dữ liệu (như CyberGlove, Manus Prime X) gắn trực tiếp các cảm biến uốn cong (Flex Sensors) và cảm biến quán tính (IMU) dọc theo từng đốt ngón tay. Mặc dù đạt độ chính xác cơ học rất cao và không bị ảnh hưởng bởi hiện tượng che khuất tầm nhìn, giải pháp này hoàn toàn đi ngược lại triết lý tương tác tự nhiên không chạm (Touchless Interaction), gây vướng víu cho người sử dụng và có chi phí phần cứng lên tới hàng nghìn đô-la Mỹ, không khả thi cho ứng dụng đại trà (Ge et al., 2019).")
    add_p("Nhóm giải pháp thương mại thứ hai sử dụng các cảm biến chiều sâu phát tia hồng ngoại có cấu trúc (Structured Light) hoặc đo thời gian bay của ánh sáng (Time-of-Flight - ToF), tiêu biểu là các dòng thiết bị Ultraleap Leap Motion Controller, Microsoft Azure Kinect và Intel RealSense D435i. Các hệ thống này cung cấp bản đồ đám mây điểm 3D (Point Cloud) giúp tách biệt bàn tay khỏi phông nền một cách dễ dàng. Tuy nhiên, phân tích thực tiễn triển khai cho thấy mỗi dòng cảm biến thương mại vẫn tồn tại những rào cản kỹ thuật và kinh tế đáng kể:")
    add_bullet("Ultraleap Leap Motion Controller: Sử dụng cặp camera hồng ngoại stereo kết hợp đèn LED hồng ngoại bước sóng 850 nm cho tốc độ quét khung xương rất cao (lên tới 120 Hz). Tuy nhiên, trường nhìn hiệu dụng (Effective Field of View) của thiết bị khá hẹp (tối ưu trong khoảng 20 cm đến 60 cm phía trên cảm biến), dễ bị nhiễu nặng dưới ánh sáng mặt trời gay gắt và đòi hỏi người dùng phải mua sắm, lắp đặt thêm thiết bị ngoại vi rời ngoài máy tính.")
    add_bullet("Microsoft Kinect / Intel RealSense RGB-D: Cung cấp đồng thời kênh màu RGB và kênh chiều sâu Depth trên phạm vi phòng rộng, rất phù hợp cho theo dõi khung xương toàn thân. Dù vậy, độ phân giải bản đồ chiều sâu ở vùng chi tiết nhỏ như các đốt ngón tay khi ở khoảng cách trên 1 m thường bị nhiễu hạt (Depth Quantization Noise) ở rìa ngón tay, đồng thời dòng sản phẩm Azure Kinect đã ngừng sản xuất thương mại, gây rủi ro lớn về khả năng duy trì phần cứng lâu dài.")
    add_bullet("Nền tảng theo dõi tay tích hợp trên kính thực tế ảo (Meta Quest Hand Tracking / Apple Vision Pro): Đạt chất lượng theo dõi cực kỳ xuất sắc nhờ hệ thống đa camera hồng ngoại gắn quanh đầu, song đây là hệ sinh thái đóng hoàn toàn, không thể trích xuất để phục vụ điều khiển hệ điều hành Windows trên máy tính xách tay hay máy tính để bàn phổ thông.")

    add_h1("2.3 CÁC GIẢI PHÁP VÀ THƯ VIỆN THỊ GIÁC MÁY TÍNH MÃ NGUỒN MỞ")
    add_p("Để khắc phục rào cản phụ thuộc vào phần cứng chuyên dụng, cộng đồng nghiên cứu thị giác máy tính mã nguồn mở đã tập trung phát triển các mô hình học sâu ước lượng tư thế bàn tay trực tiếp từ một camera RGB thông thường (Monocular RGB Hand Pose Estimation). Trong hệ sinh thái mã nguồn mở hiện nay, ba trường phái kiến trúc nổi bật nhất bao gồm: phương pháp tiếp cận từ dưới lên đa nhánh (Bottom-up Multi-person Pose) đại diện bởi OpenPose (Simon et al., 2017); phương pháp đường ống hai giai đoạn chạy trên thiết bị di động đại diện bởi Google MediaPipe Hands (Zhang et al., 2020); và phương pháp phát hiện tư thế một giai đoạn hợp nhất đại diện bởi dòng mô hình Ultralytics YOLO-Pose (Jocher, Qiu, & Chaurasia, 2024).")
    add_p("Mỗi thư viện và kiến trúc mã nguồn mở đều sở hữu những ưu thế và giới hạn kỹ thuật riêng biệt khi đặt vào bài toán tương tác thời gian thực trên máy tính cá nhân. OpenPose sử dụng kỹ thuật Trường ái lực bộ phận (Part Affinity Fields - PAFs) kết hợp phép lấy mẫu đa góc nhìn (Multiview Bootstrapping) để tái tạo đồng thời khung xương cơ thể, khuôn mặt và 21 điểm bàn tay. Tuy nhiên, khối lượng tính toán tích chập đa tầng của OpenPose cực kỳ nặng nề, đòi hỏi card đồ họa máy trạm cao cấp mới đạt được 10–15 FPS, không phù hợp cho các tác vụ điều khiển âm lượng hay gõ chữ yêu cầu độ phản hồi tức thì. Ngược lại, Google MediaPipe Hands thiết kế kiến trúc gồm bộ phát hiện lòng bàn tay nhẹ (BlazePalm Detector) kết hợp mạng hồi quy 21 điểm mốc 3D chạy rất hiệu quả trên CPU. Điểm yếu của MediaPipe thuần túy là cơ chế bám vết (Tracking-by-Detection) dựa trên khung hình trước đó: khi người dùng di chuyển bàn tay với vận tốc cao hoặc đưa tay ở khoảng cách xa trong khung hình rộng, bộ bám vết dễ bị trượt ROI, dẫn đến mất dấu hoặc định vị sai bàn tay trên các vùng nhiễu nền có màu tương tự màu da.")
    add_p("Sự ra đời của kiến trúc YOLOv8-Pose và mới nhất là YOLOv11-Pose (Ultralytics, 2024) đã mở ra hướng tiếp cận đột phá: toàn bộ bức ảnh đầu vào được mạng Backbone C3k2 và khối chú ý không gian C2PSA xử lý chỉ trong một lượt lan truyền tiến (Single Forward Pass) duy nhất trên nhân CUDA GPU, dự đoán đồng thời hộp bao bàn tay và véc-tơ 21 điểm khớp xương với thời gian suy luận chỉ khoảng 6–9 ms. Tuy nhiên, do YOLO-Pose phải tối ưu hóa trên toàn bộ không gian ảnh lớn (ví dụ 512x512 hoặc 640x640), độ phân giải hiệu dụng dành cho vùng bàn tay nhỏ đôi khi chưa đủ mịn để phân biệt chính xác độ sâu tương đối khi các ngón tay đan chéo phức tạp trong bảng chữ cái ASL (như các chữ M, N, T, S, E). Chính vì vậy, việc kết hợp có chọn lọc giữa YOLOv11-Pose và MediaPipe 3D tạo nên một giải pháp cộng hưởng hoàn hảo, khắc phục triệt để nhược điểm của từng mô hình đơn lẻ.")

    t21_comp_headers = ["Tiêu chí đánh giá", "Cảm biến Depth (Leap Motion / RealSense)", "OpenPose (CMU Multi-view)", "MediaPipe Hands (Google thuần túy)", "Hybrid YOLOv11-Pose + MP3D (Đề tài)"]
    t21_comp_data = [
        ["Yêu cầu phần cứng", "Phụ thuộc cảm biến hồng ngoại/RGB-D rời đắt tiền ($100 - $400)", "Đòi hỏi GPU máy trạm dung lượng VRAM lớn (>= 8 GB)", "Webcam RGB phổ thông, chạy trên CPU/GPU nhẹ", "Webcam RGB phổ thông + Tối ưu hóa GPU CUDA / CPU"],
        ["Khả năng bắt tay ở cự ly xa / vận tốc cao", "Giới hạn trong vùng không gian hẹp (20 - 60 cm)", "Tốt nhưng tốc độ khung hình rất thấp gây trễ", "Dễ mất dấu khi vung tay nhanh hoặc tay nhỏ ở xa", "Rất xuất sắc nhờ YOLOv11-Pose quét toàn cục mỗi frame"],
        ["Độ chính xác khớp 3D cục bộ (Sub-pixel)", "Rất cao trong vùng trường nhìn ngắn", "Tốt trên khớp 2D, không có tọa độ 3D tương đối", "Cao khi ROI bàn tay đã được cắt chuẩn xác", "Tuyệt đối nhờ MediaPipe 3D chạy trên ROI mở rộng 45%"],
        ["Khử rung nhiễu (Jitter) & Chống nhảy chữ", "Phụ thuộc SDK đóng của hãng sản xuất", "Không tích hợp sẵn bộ lọc tương tác HCI", "Rung nhẹ ở đầu ngón tay khi giữ tĩnh", "Tích hợp One-Euro Filter (giảm 93,8% rung) & VotingBuffer"],
        ["Tốc độ thực thi thực tế (FPS)", "60 - 120 FPS (yêu cầu USB 3.0 chuyên dụng)", "8 - 15 FPS (không đạt chuẩn tương tác mượt)", "24 - 32 FPS trên CPU", "45,2 FPS trên GPU RTX 4050 (độ trễ chỉ 22,1 ms)"],
    ]
    add_custom_table("2.1", "So sánh đặc tính các nền tảng nhận diện cử chỉ thương mại và mã nguồn mở",
                     t21_comp_headers, t21_comp_data, [3.1, 3.1, 2.9, 3.1, 3.3], [],
                     "Tổng hợp từ tài liệu kỹ thuật Ultralytics, Google MediaPipe và thực nghiệm năm 2026")

    add_h1("2.4 TIÊU CHÍ SO SÁNH VÀ KIẾN TRÚC PHÂN TẦNG HỆ THỐNG HYBRID")
    add_p("Kiến trúc phần mềm của một hệ thống thị giác máy tính tương tác thời gian thực cần tách bạch rõ ràng giữa tầng thu nhận - suy luận học sâu, tầng xử lý tín hiệu - điều phối nghiệp vụ và tầng giao diện hiển thị người dùng. Nếu toàn bộ mã lệnh đọc camera, chạy mô hình nơ-ron, lọc toán học và gọi hàm API hệ điều hành đều đặt chung trong một vòng lặp đơn luồng (Single-threaded Loop), giao diện đồ họa sẽ ngay lập tức bị treo cứng (UI Freezing) mỗi khi GPU thực hiện truy vấn hoặc khi bộ tổng hợp giọng nói phát âm câu văn. Cách tổ chức phân tầng đa luồng không chỉ giúp cô lập độ trễ giữa các mô-đun mà còn cho phép kiểm thử độc lập từng thành phần, dễ dàng thay thế trọng số mô hình mới hoặc bổ sung các tập lệnh điều khiển mới mà không làm xáo trộn cấu trúc tổng thể.")
    add_p("Khả năng tương tác mượt mà giữa mô hình học sâu và hệ điều hành còn đòi hỏi sự chuẩn hóa chặt chẽ về cấu trúc dữ liệu trung gian. Trong hệ thống đề xuất, mọi kết quả suy luận từ tầng AI đều được đóng gói thống nhất vào đối tượng cấu trúc dữ liệu bất biến `HandPoseAnalysis` (định nghĩa bằng `@dataclass` trong Python), bao gồm tọa độ hộp bao `bbox = (x1, y1, x2, y2)`, ma trận khớp xương đã làm mượt `keypoints` kích thước (21, 3), độ tự tin phát hiện `det_confidence`, danh sách trạng thái 5 ngón tay `fingers_up = [Thumb, Index, Middle, Ring, Pinky]`, nhãn ký hiệu `asl_label`, độ tự tin `asl_confidence`, nhãn lệnh điều khiển `control_gesture` và tỷ lệ khoảng cách chụm ngón `pinch_ratio` thuộc đoạn [0.0, 1.0]. Nhờ giao kèo dữ liệu tường minh này, tầng giao diện và tầng điều khiển hoàn toàn không cần biết chi tiết nội bộ của mạng nơ-ron bên dưới.")

    add_figure("report_assets/fig_2_1_layered_arch.png", "2.2",
               "Sơ đồ kiến trúc phân tầng 3 lớp hệ thống nhận diện cử chỉ và điều khiển không chạm",
               "Tác giả thiết kế và tổng hợp, 2026", width_in=5.8)

    add_p("Kiến trúc hệ thống đề xuất bao gồm 3 tầng chức năng chính hoạt động hiệp đồng:")
    add_p("1. Tầng mô hình học sâu và cơ sở dữ liệu đặc trưng (AI & Data Engine Layer): Chịu trách nhiệm thực thi đường ống suy luận hai giai đoạn (Two-Stage Hybrid Inference). Ở giai đoạn 1, mô hình `yolo11n_hand_pose_best.pt` chạy trên nhân CUDA của GPU NVIDIA để định vị nhanh hộp bao bàn tay và 21 điểm khớp sơ bộ. Ở giai đoạn 2, hộp bao được mở rộng biên 45% (ROI Padding) và chuyển cho mô hình `gesture_recognizer.task` của MediaPipe 3D để trích xuất tọa độ 3D sub-pixel cùng nhãn cử chỉ nơ-ron, đồng thời đối chiếu với cơ sở dữ liệu mẫu cá nhân hóa `asl_keypoints_db.npz`.")
    add_p("2. Tầng điều phối logic, lọc tín hiệu và điều khiển hệ thống (Controller & Signal Layer): Tiếp nhận ma trận 21 khớp xương thô, áp dụng bộ lọc thông thấp thích ứng One-Euro Filter để khử nhiễu rung tọa độ, sau đó giải tích hình học góc khớp để phân loại cử chỉ. Tại đây, các bộ lọc hậu kỳ gồm `VotingBuffer`, `CommandCooldown` và `ExponentialMovingAverage` kiểm soát chặt chẽ tính ổn định trước khi phát lệnh điều khiển âm lượng qua PyCAW Core Audio, gửi phím tắt qua Win32 `SendInput` hoặc kích hoạt bộ gợi ý từ và phát âm giọng nói `pyttsx3`.")
    add_p("3. Tầng trình diễn và giao diện người dùng (Presentation Layer - PyQt6): Được xây dựng trên nền tảng PyQt6 Modern Dark UI, giao tiếp bất đồng bộ với tầng xử lý thông qua cơ chế `QTimer` và luồng nền `ThreadedCamera`. Tầng này hiển thị trực quan khung xương 21 điểm với mã màu riêng biệt cho từng ngón tay, thước đo phần trăm âm lượng Pinch Volume trên màn hình HUD, thanh tiến trình giữ cử chỉ, bảng soạn thảo văn bản ASL và hộp thoại hướng dẫn trực quan `ASLGuideDialog`.")

    add_figure("report_assets/fig_2_2_dataflow.png", "2.3",
               "Luồng trao đổi dữ liệu khung hình và sự kiện điều khiển đa luồng thời gian thực",
               "Tác giả tổng hợp theo kiến trúc hệ thống, 2026", width_in=5.7)

    # -------------------------------------------------------------------------
    # CHƯƠNG 3: MÃ NGUỒN, THUẬT TOÁN HỌC SÂU YOLOV11-POSE VÀ BỘ LỌC TÍN HIỆU THÍCH NGHI
    # -------------------------------------------------------------------------
    doc.add_page_break()
    add_chap_header(3, "MÃ NGUỒN, THUẬT TOÁN HỌC SÂU YOLOV11-POSE VÀ BỘ LỌC TÍN HIỆU THÍCH NGHI")

    add_h1("3.1 NGUYÊN LÝ MẠNG YOLOV11-POSE VÀ CƠ CHẾ HỢP NHẤT MEDIAPIPE 3D")
    add_p("Trong quá trình xây dựng hệ thống nhận diện tư thế bàn tay thời gian thực, việc thiết kế kiến trúc mô hình cốt lõi quyết định trực tiếp đến sự cân bằng giữa độ chính xác không gian và tốc độ phản hồi. Hệ thống đề xuất triển khai lớp `YoloPoseHandDetector` (tại tệp mã nguồn `src/core/detector.py`), kết hợp sức mạnh của mạng tích chập thế hệ mới nhất Ultralytics YOLOv11-Pose (Jocher, Qiu, & Chaurasia, 2024) và mô hình tinh chỉnh không gian ba chiều MediaPipe HandLandmarker (Zhang et al., 2020). Về mặt cấu trúc mạng, YOLOv11-Pose cải tiến mạnh mẽ bộ khung trích xuất đặc trưng (Backbone) và cổ mạng tổng hợp đa tỷ lệ (Neck PANet/FPN) bằng cách thay thế khối C2f truyền thống bằng khối C3k2 (Cross Stage Partial with kernel size 2) kết hợp mô-đun chú ý không gian theo điểm C2PSA (Convolutional Block with Parallel Spatial Attention). Cơ chế chú ý không gian C2PSA giúp mạng nơ-ron tập trung trọng số kích hoạt vào các vùng có mật độ cạnh và cấu trúc khớp cao như các ngón tay, giảm thiểu hiện tượng kích hoạt nhầm trên các vật thể nền phức tạp.")
    add_p("Đầu ra của mạng YOLOv11-Pose sử dụng kiến trúc Đầu dự đoán tách biệt (Decoupled Pose Head) gồm ba nhánh song song trên mỗi ô lưới đa tỷ lệ: nhánh hồi quy hộp bao dự đoán 4 tọa độ (x, y, w, h); nhánh phân loại đối tượng dự đoán xác suất hiện diện bàn tay; và nhánh hồi quy điểm mốc dự đoán trực tiếp 21 bộ ba giá trị (x_i, y_i, v_i) tương ứng với tọa độ điểm ảnh và độ tự tin hiển thị (Visibility Confidence) của 21 khớp xương. Trong quá trình huấn luyện trên GPU, hàm mất mát tổng hợp của mạng được tối ưu hóa đồng thời qua bốn thành phần toán học:")
    add_formula("L_total = λ_box * L_CIoU + λ_dfl * L_DFL + λ_cls * L_BCE + λ_pose * L_OKS", "3.1")
    add_p("Trong công thức (3.1), L_CIoU là hàm mất mát Complete IoU xét đến diện tích giao thoa, khoảng cách tâm và tỷ lệ khung hình của hộp bao bàn tay; L_DFL là Distribution Focal Loss giúp mạng hội tụ chính xác biên hộp bao dưới dạng phân phối xác suất rời rạc; L_BCE là hàm mất mát entropy chéo nhị phân cho nhãn lớp và độ hiển thị khớp; còn L_OKS là hàm mất mát dựa trên Độ tương đồng điểm mốc đối tượng (Object Keypoint Similarity - OKS), được định nghĩa chặt chẽ như sau:")
    add_formula("OKS = [ Σ_{i=0}^{20} exp( - d_i^2 / (2 * s^2 * k_i^2) ) * δ(v_i > 0) ] / [ Σ_{i=0}^{20} δ(v_i > 0) ]", "3.2")
    add_p("Với d_i là khoảng cách Euclid giữa tọa độ dự đoán và tọa độ nhãn thực (Ground Truth) của khớp thứ i; s là căn bậc hai diện tích hộp bao bàn tay; và k_i là hằng số độ lệch chuẩn đặc trưng của từng khớp giải phẫu bàn tay. Tuy nhiên, thực nghiệm cho thấy khi chỉ sử dụng YOLOv11-Pose thuần túy ở độ phân giải suy luận nhanh (`imgsz = 512`), một số điểm đầu mút ngón tay (TIP: các điểm 8, 12, 16, 20) đôi khi bị dự đoán gập ngược bất thường về phía khớp bàn đốt (MCP) khi ngón tay di chuyển quá nhanh. Để khắc phục hiện tượng này ngay ở cấp độ hình học, đề tài đã phát triển thuật toán hiệu chỉnh giải phẫu `_anatomical_correct_keypoints`: với mỗi chuỗi ngón tay (MCP, PIP, DIP, TIP), thuật toán tính véc-tơ đốt giữa v_1 = p_DIP - p_PIP và véc-tơ đốt xa v_2 = p_TIP - p_DIP. Nếu cosin góc định hướng cos(θ) < -0,20 đồng thời khoảng cách từ TIP tới MCP nhỏ hơn từ DIP tới MCP, tọa độ điểm đầu ngón p_TIP sẽ được tái cấu trúc tuyến tính theo hướng véc-tơ đốt giữa với hệ số tỷ lệ giải phẫu γ thuộc {0,82; 0,85; 0,82; 0,78}:")
    add_formula("p_TIP_corrected = p_DIP + γ * (p_DIP - p_PIP)", "3.3")

    add_figure("report_assets/fig_3_1_hybrid_fusion.png", "3.1",
               "Cơ chế học kết hợp đa mô hình (Hybrid YOLOv11-Pose, MediaPipe 3D và 1€ Filter)",
               "Mô phỏng theo kiến trúc mã nguồn src/core/detector.py, 2026", width_in=5.7)

    add_p("Điểm đột phá quan trọng nhất trong kiến trúc của đề tài là cơ chế hợp nhất hai giai đoạn trong phương thức `_refine_with_mediapipe_3d`. Ngay khi giai đoạn 1 (YOLOv11-Pose trên GPU `cuda:0`) định vị được hộp bao bàn tay `yolo_bbox = (x1, y1, x2, y2)`, hệ thống lập tức tính toán vùng quan tâm mở rộng (Padded ROI) với khoảng đệm lề `pad = 0,45 * max(bw, bh)` về cả bốn phía nhằm đảm bảo toàn bộ các ngón tay xòe rộng đều nằm gọn trong vùng cắt. Vùng ảnh ROI này (với kích thước tối thiểu 64x64 pixel) được chuyển sang không gian màu SRGB và đưa vào bộ nhận diện MediaPipe 3D GestureRecognizer. Khi MediaPipe trích xuất thành công 21 điểm mốc trên vùng ROI cục bộ, tọa độ chuẩn hóa [0, 1] của MediaPipe được ánh xạ ngược về hệ tọa độ khung hình gốc theo công thức: x_global = cx_1 + lm.x * rw và y_global = cy_1 + lm.y * rh. Trong trường hợp bàn tay ở quá gần hoặc góc nghiêng đặc biệt khiến YOLO tạm thời bỏ sót nhưng MediaPipe quét toàn khung hình phát hiện được, hoặc ngược lại khi MediaPipe bị lóa sáng nhưng YOLO trên GPU vẫn bám tốt, cơ chế hợp nhất (Fallback Fusion) sẽ tự động chọn nguồn tọa độ khả dụng tốt nhất, giúp tỷ lệ phát hiện bàn tay liên tục đạt gần như tuyệt đối.")

    add_h1("3.2 CÁC SIÊU THAM SỐ CỐT LÕI CỦA YOLOV11-POSE VÀ BỘ LỌC ONE-EURO FILTER")
    add_p("Để hệ thống vận hành ở trạng thái tối ưu trên cả phương diện độ chính xác nhận diện lẫn độ mượt tương tác thời gian thực, các siêu tham số (Hyperparameters) của mô hình học sâu YOLOv11-Pose, bộ tinh chỉnh MediaPipe và bộ lọc tín hiệu số One-Euro Filter cần được thiết lập và tinh chỉnh có cơ sở khoa học. Trong bài toán theo dõi bàn tay tương tác, ngay cả khi mạng nơ-ron đạt độ chính xác rất cao trên từng khung hình tĩnh độc lập, sự dao động vi mô của cường độ sáng trên cảm biến CMOS của Webcam vẫn tạo ra nhiễu tần số cao (High-frequency Sensor Jitter) làm các điểm khớp xương rung lắc liên tục từ 3 đến 8 pixel giữa các khung hình kế tiếp. Nếu sử dụng bộ lọc trung bình trượt thông thường với hệ số làm mượt cố định, hiện tượng rung khi giữ yên tay sẽ giảm nhưng lại phát sinh độ trễ quán tính lớn khi người dùng di chuyển tay nhanh để kéo thanh âm lượng.")
    add_p("Nhằm giải quyết triệt để mâu thuẫn giữa khử nhiễu tĩnh và giảm độ trễ động, lớp `OneEuroFilter` trong tệp `src/core/smoother.py` hiện thực hóa bộ lọc thông thấp bậc một có tần số cắt thích nghi theo vận tốc (Casiez, Roussel, & Vogel, 2012). Gọi T_e = t_k - t_{k-1} là khoảng thời gian lấy mẫu giữa hai khung hình liên tiếp và x_k là tọa độ điểm khớp tại thời điểm hiện tại. Trước hết, vận tốc biến thiên tọa độ dx_k = (x_k - x_hat_{k-1}) / T_e được làm mượt bằng một bộ lọc thông thấp có tần số cắt đạo hàm cố định d_cutoff = 1,0 Hz để thu được vận tốc ước lượng dx_hat_k. Sau đó, tần số cắt chính f_c của bộ lọc vị trí được điều chỉnh động tuyến tính theo độ lớn vận tốc chuyển động của bàn tay:")
    add_formula("f_c(k) = f_min_cutoff + β * |dx_hat_k|   với   α(T_e, f_c) = (2π * f_c * T_e) / (2π * f_c * T_e + 1)", "3.4")
    add_formula("x_hat_k = α(T_e, f_c) * x_k + (1 - α(T_e, f_c)) * x_hat_{k-1}", "3.5")
    add_p("Trong đó, `min_cutoff` (f_min_cutoff = 1,4 Hz) quy định ngưỡng lọc cực đại khi bàn tay đứng yên (|dx_hat_k| ≈ 0), giúp triệt tiêu hoàn toàn hiện tượng rung khung xương; còn hệ số tốc độ `beta` (β = 0,035) quyết định tốc độ mở rộng băng thông khi bàn tay chuyển động nhanh: khi vận tốc tăng cao, f_c tăng vọt làm hệ số α tiến sát về 1,0, giúp tọa độ đầu ra x_hat_k bám sát tức thời tọa độ thực x_k với độ trễ gần như bằng không. Đặc biệt, thuật toán còn tích hợp ngưỡng bảo vệ bước nhảy không gian (`jump_dist > 140,0` pixel): khi bàn tay mới xuất hiện ở một vị trí khác xa vị trí cũ, bộ lọc tự động khởi tạo lại trạng thái ngay lập tức thay vì kéo vệt xương bay ngang qua màn hình.")

    t31_hyper_headers = ["Tên siêu tham số", "Giá trị thiết lập", "Dải tinh chỉnh khuyến nghị", "Ý nghĩa và tác động kỹ thuật trong hệ thống"]
    t31_hyper_data = [
        ["imgsz (YOLO Input)", "512 (Suy luận)\n640 (Huấn luyện)", "416 – 640 pixel", "Kích thước тен-xơ ảnh đầu vào mạng YOLOv11-Pose; mức 512 tối ưu hóa tốc độ GPU đạt >45 FPS mà vẫn giữ độ nét khớp."],
        ["conf_threshold", "0,32", "0,25 – 0,50", "Ngưỡng độ tự tin tối thiểu để YOLOv11 chấp nhận hộp bao bàn tay trước khi chuyển sang giai đoạn tinh chỉnh ROI."],
        ["roi_padding_ratio", "0,45 (45%)", "0,25 – 0,55", "Tỷ lệ mở rộng biên hộp bao YOLO khi cắt ảnh ROI cho MediaPipe 3D, ngăn chặn việc cắt cụt các đầu ngón tay khi xòe rộng."],
        ["min_cutoff (1€ Filter)", "1,4 Hz", "0,8 – 2,0 Hz", "Tần số cắt tối thiểu khi bàn tay giữ tĩnh; giá trị càng nhỏ khung xương càng đứng im tuyệt đối nhưng tăng nhẹ quán tính."],
        ["beta (1€ Speed Coeff.)", "0,035", "0,005 – 0,080", "Hệ số khuếch đại tần số cắt theo vận tốc |dx/dt|; giúp triệt tiêu hoàn toàn độ trễ pha khi người dùng vung tay nhanh."],
        ["window_size & min_votes", "W = 12 frames\nmin_votes = 8", "W: 8 – 15\nmin_votes: 5 – 10", "Kích thước cửa sổ trượt và số phiếu tối thiểu trong VotingBuffer để chốt một ký tự ASL, chống nhảy chữ tuyệt đối."],
        ["ema_alpha (Pinch Vol)", "0,25", "0,15 – 0,40", "Hệ số làm mượt hàm mũ cho tỷ lệ khoảng cách chụm ngón cái - ngón trỏ khi điều chỉnh thanh âm lượng Windows 0-100%."],
    ]
    add_custom_table("3.1", "Các siêu tham số cốt lõi của mô hình YOLOv11-Pose và bộ lọc One-Euro Filter",
                     t31_hyper_headers, t31_hyper_data, [3.5, 2.7, 2.8, 6.5], [],
                     "Trích xuất từ cấu hình thực thi trong src/core/detector.py và src/core/smoother.py, 2026")

    add_h1("3.3 THIẾT LẬP ĐƯỜNG ỐNG (PIPELINE) TIỀN XỬ LÝ, CHUẨN HÓA 42 CHIỀU VÀ HUẤN LUYỆN")
    add_p("Một hệ thống nhận diện cử chỉ có khả năng tái lập và cá nhân hóa cao đòi hỏi quy trình tiền xử lý và trích xuất đặc trưng hình học phải bất biến đối với cả phép tịnh tiến (vị trí bàn tay nằm ở góc trái, góc phải hay giữa màn hình) lẫn phép vị tự tỷ lệ (bàn tay đưa lại gần hay để ra xa ống kính Webcam). Trong lớp `HandPoseAnalyzer` (`src/core/pose_analyzer.py`), đề tài thiết lập đường ống chuẩn hóa hình học thông qua phương thức `extract_normalized_features`. Từ ma trận 21 điểm khớp xương 2D P = {p_0, p_1, ..., p_20} với p_i = (x_i, y_i), bước đầu tiên thực hiện phép tịnh tiến toàn bộ hệ tọa độ về gốc cổ tay p_0 = (x_0, y_0), thu được tập véc-tơ tương đối r_i = p_i - p_0. Bước thứ hai tìm bán kính bao lớn nhất từ cổ tay tới điểm xa nhất trên bàn tay R_max = max_{i} ||r_i||_2 (với ngưỡng an toàn R_max >= 10^-5) và chia chuẩn hóa toàn bộ các tọa độ tương đối cho R_max trước khi trải phẳng (Flatten) thành một véc-tơ đặc trưng 42 chiều duy nhất:")
    add_formula("f_norm = (1 / max_j ||p_j - p_0||_2) * [ (x_0 - x_0), (y_0 - y_0), ..., (x_20 - x_0), (y_20 - y_0) ]^T ∈ R^42", "3.6")

    add_figure("report_assets/fig_3_2_pipeline_5steps.png", "3.2",
               "Quy trình đường ống (Pipeline) 5 bước tiền xử lý, chuẩn hóa 42-D và suy luận",
               "Tác giả thiết kế theo quy chuẩn xử lý của hệ thống, 2026", width_in=5.8)

    add_p("Trước khi đưa ma trận khớp xương vào bộ giải cử chỉ, hệ thống thực thi chốt chặn kiểm định tính hợp lệ cơ sinh học `is_valid_hand_skeleton` nhằm loại bỏ các khung hình nhiễu hoặc chưa hội tụ. Cụ thể, một khung xương 21 điểm chỉ được công nhận là hợp lệ khi thỏa mãn đồng thời ba bất đẳng thức hình học: (1) Độ mở sải tay `kpt_span` phải đạt tối thiểu 18% đường chéo hộp bao (`kpt_span >= 0,18 * box_diag`); (2) Chiều dài trục lòng bàn tay từ cổ tay (điểm 0) đến khớp gốc ngón giữa (điểm 9) phải đạt tối thiểu 10% đường chéo hộp bao (`palm_len >= 0,10 * box_diag`); và (3) Tỷ lệ độ gấp khúc ngang của chuỗi khớp bàn đốt từ ngón trỏ sang ngón út `(d_{5,9} + d_{9,13} + d_{13,17}) / d_{5,17}` không được vượt quá 2,6. Nếu bất kỳ điều kiện nào bị vi phạm, khung hình đó sẽ bị gán nhãn `NOTHING` / `NONE`, ngăn chặn hoàn toàn việc phát sinh lệnh điều khiển sai.")
    add_p("Ở bước tiếp theo của đường ống, phương thức `get_finger_states` xác định véc-tơ trạng thái nhị phân 5 chiều F = [t, i, m, r, p] ∈ {0, 1}^5 đại diện cho trạng thái mở (1) hoặc gập (0) của 5 ngón tay. Với 4 ngón tay dài (trỏ, giữa, áp út, út), một ngón tay được xác nhận là duỗi mở khi góc khớp gian đốt gần θ_PIP = ∠([MCP, PIP, DIP]) > 130°, góc khớp gian đốt xa θ_DIP = ∠([PIP, DIP, TIP]) > 125°, đồng thời khoảng cách từ đầu ngón TIP tới cổ tay và tâm lòng bàn tay lớn hơn khoảng cách tương ứng từ khớp PIP và MCP một lượng bù tỷ lệ kích thước lòng bàn tay (`0,05 * palm_size` và `0,18 * palm_size`). Riêng đối với ngón cái có cơ chế vận động khép ngang đặc thù, trạng thái mở được xác lập khi góc ∠([1, 2, 4]) > 130°, góc ∠([2, 3, 4]) > 135° và khoảng cách từ đầu ngón cái (điểm 4) tới gốc ngón út (điểm 17) vượt trội hơn khoảng cách từ khớp MCP ngón cái (điểm 2) tới điểm 17.")

    t32_rules_headers = ["Nhóm tác vụ", "Nhãn đầu ra", "Điều kiện véc-tơ ngón F = [t,i,m,r,p]", "Ràng buộc hình học không gian 21 khớp & Tác vụ thực thi"]
    t32_rules_data = [
        ["Touchless Control", "PINCH_VOLUME", "[1, 1, 0, 0, 0] (Chế độ Pinch bật)", "Nội suy tuyến tính d(4,8) trong đoạn [0,18*palm, 1,25*palm] -> Âm lượng PyCAW 0% - 100%."],
        ["Touchless Control", "OPEN_PALM / FIST", "[1, 1, 1, 1, 1] hoặc [0, 0, 0, 0, 0]", "Xòe 5 ngón: Phát/Tạm dừng Media (0xB3); Nắm 5 ngón: Bật/Tắt tiếng Mute (0xAD)."],
        ["Touchless Control", "THUMBS_UP / DOWN", "[1, 0, 0, 0, 0] hoặc nắm tay giơ cái", "Độ lệch dọc dy = y_4 - y_2 < -0,18*palm (Tăng Vol +6%) hoặc dy > +0,18*palm (Giảm Vol -6%)."],
        ["Touchless Control", "POINT_RIGHT / LEFT", "[_, 1, 0, 0, 0] (Chỉ ngón trỏ mở)", "Độ lệch ngang |x_8 - x_5| > 0,30*palm: Dương -> Qua bài (0xB0); Âm -> Lùi bài (0xB1)."],
        ["Touchless Control", "PEACE (Victory)", "[0, 1, 1, 0, 0] (Trỏ & giữa mở)", "Cử chỉ chữ V ổn định qua 4 frames -> Chụp ảnh màn hình lưu vào thư mục screenshots/."],
        ["ASL Translator", "Nhóm duỗi thẳng (B, W, Y, I, L, V, U, R, K)", "Tổ hợp nhị phân đặc trưng từng chữ", "Phân tách V/U/R qua khoảng cách chuẩn hóa d(8,12)/palm (<0,16: R; <0,28: U; >=0,28: V); K có thêm t=1."],
        ["ASL Translator", "Nhóm nắm & cong (A, O, C, S, E, M, N, T, X)", "[0, 0, 0, 0, 0] hoặc [1, 0, 0, 0, 0]", "Phân tách O (d(4,8)<0,28), C (75°<θ_PIP<135°), M/N/T (vị trí đầu ngón cái luồn dưới áp út/giữa/trỏ), S và E."],
        ["ASL Translator", "SPACE / DEL", "[1, 1, 1, 1, 1] / [0, 1, 0, 0, 0] nghiêng trái", "Xòe 5 ngón chèn khoảng trắng (SPACE); Ngón trỏ nghiêng trái dx < -0,42*palm xóa ký tự cuối (DEL)."],
    ]
    add_custom_table("3.2", "Quy tắc ánh xạ giải tích hình học 21 khớp sang cử chỉ Touchless và ASL",
                     t32_rules_headers, t32_rules_data, [2.6, 3.0, 3.4, 6.5], [],
                     "Tổng hợp từ giải thuật phân loại trong src/core/pose_analyzer.py, 2026")

    add_h1("3.4 CHIẾN LƯỢC PHÂN CHIA DỮ LIỆU, BỘ ĐỆM VOTINGBUFFER VÀ GIỚI HẠN MÔ HÌNH")
    add_p("Trong quá trình huấn luyện mô hình YOLOv11-Pose bằng kịch bản `scripts/train_yolov11_pose_gpu.py`, chiến lược phân chia dữ liệu và tăng cường dữ liệu hình học (Geometric Data Augmentation) đóng vai trò quyết định đến khả năng chống quá khớp (Overfitting). Tập dữ liệu bàn tay chuẩn được chia tách nghiêm ngặt theo tỷ lệ độc lập giữa tập huấn luyện (Training Set) và tập kiểm định (Validation Set), đồng thời cấu hình các phép biến đổi tăng cường có kiểm soát: dịch chuyển khung hình (`translate = 0,1`), co giãn tỷ lệ (`scale = 0,4`), xoay góc nghiêng (`degrees = 15,0°`), ghép mảnh bốn ảnh (`mosaic = 0,8` và tắt dần trong 10 epoch cuối `close_mosaic = 10`). Đặc biệt, hệ thống thiết lập `fliplr = 0,0` (tắt lật ngang ngẫu nhiên không có ánh xạ nhãn đối xứng) để bảo toàn tính nhất quán thứ tự topo của 21 khớp xương bàn tay, kết hợp bộ tối ưu hóa `AdamW` với lịch trình giảm tốc độ học dạng hàm cosin (`cos_lr = True`, khởi đầu từ `lr0 = 0,001` giảm dần về `lrf = 0,01`).")
    add_p("Khi triển khai mô hình vào luồng video trực tiếp 30–60 FPS, một thách thức lớn nảy sinh ở giai đoạn chuyển tiếp cử chỉ (Gesture Transition Phase): khi người dùng đang biến đổi thế tay từ chữ cái 'A' sang chữ cái 'B', trong khoảng 3 đến 5 khung hình trung gian, các ngón tay đang duỗi dở dang có thể vô tình rơi vào vùng quyết định của chữ 'E' hoặc chữ 'C'. Để giải quyết triệt để bài toán này, đề tài thiết kế lớp `VotingBuffer` (`src/core/smoother.py`) hoạt động theo cơ chế cửa sổ trượt bỏ phiếu đa số có khóa chống lặp:")
    add_formula("y_committed = c*   nếu   Count(c* trong W=12 frames) >= 8   và   c* != y_last_committed", "3.7")
    add_p("Theo cơ chế (3.7), một nhãn chữ cái chỉ được chốt vào văn bản khi xuất hiện tối thiểu 8 lần trong cửa sổ 12 khung hình gần nhất với độ tự tin mỗi khung hình đạt từ 0,65 trở lên. Ngay sau khi một chữ cái được chốt (`y_last_committed = c*`), hệ thống tự động khóa nhãn đó để nếu người dùng vẫn giữ nguyên bàn tay trên không trung thì ứng dụng không gõ lặp lại thành chuỗi 'AAAAA'; khóa này chỉ được giải phóng khi người dùng đổi sang chữ cái khác hoặc hạ tay nghỉ quá 8 khung hình liên tiếp (`none_streak >= 8`). Song song đó, ở chế độ điều khiển không chạm, lớp `CommandCooldown` áp đặt số khung hình giữ tối thiểu (`required_hold_frames = 4`) kèm thời gian nghỉ riêng biệt cho từng loại lệnh (ví dụ: Play/Pause và Mute nghỉ 1,5 giây; Qua bài nghỉ 1,1 giây; Tăng/Giảm âm lượng nghỉ 0,28 giây), đảm bảo thao tác điều khiển thiết bị diễn ra chính xác, dứt khoát. Hạn chế cốt lõi còn tồn tại của bộ phân loại hình học 2D/3D trên một góc nhìn đơn lẻ là sự nhạy cảm khi mặt phẳng lòng bàn tay quay vuông góc hoàn toàn với trục quang học của camera (góc nghiêng > 75°), khi đó các khớp MCP, PIP, DIP chồng lấp lên nhau trên mặt phẳng chiếu, đòi hỏi người dùng cần sự hỗ trợ của mô-đun lưu mẫu cá nhân hóa k-NN (`reload_custom_samples`) để bù đắp sai số góc nhìn.")

    # -------------------------------------------------------------------------
    # CHƯƠNG 4: TẬP DỮ LIỆU, THỰC NGHIỆM VÀ ĐÁNH GIÁ MÔ HÌNH NHẬN DIỆN CỬ CHỈ
    # -------------------------------------------------------------------------
    doc.add_page_break()
    add_chap_header(4, "TẬP DỮ LIỆU, THỰC NGHIỆM VÀ ĐÁNH GIÁ MÔ HÌNH NHẬN DIỆN CỬ CHỈ")

    add_h1("4.1 TẬP DỮ LIỆU CHUẨN HAND-KEYPOINTS VÀ CƠ SỞ DỮ LIỆU ASL CÁ NHÂN HÓA")
    add_p("Nguồn tri thức cốt lõi giúp mạng nơ-ron YOLOv11-Pose học được quy luật giải phẫu 21 khớp xương bàn tay dưới nhiều điều kiện chiếu sáng và phông nền phức tạp phụ thuộc trực tiếp vào chất lượng của tập dữ liệu huấn luyện. Đề tài sử dụng bộ dữ liệu chuẩn Ultralytics Hand-Keypoints (được xây dựng và chuẩn hóa từ kho dữ liệu CMU Panoptic Studio và tập dữ liệu tổng hợp đa góc nhìn của Simon et al., 2017) kết hợp cùng tập dữ liệu tinh chỉnh cục bộ (`data/hand_pose_fast.yaml` và `data/hand_pose_local.yaml`). Tập dữ liệu gốc bao gồm 26.768 mẫu hình ảnh bàn tay có gắn nhãn hộp bao và tọa độ 21 điểm khớp xương theo đúng cấu trúc `kpt_shape: [21, 3]`, trong đó 18.776 mẫu được phân bổ cho tập huấn luyện (Training Set) và 7.992 mẫu dành cho tập kiểm định (Validation Set). Mỗi bản ghi nhãn trong định dạng chuẩn YOLO Pose chứa 68 giá trị số thực trên một dòng: giá trị đầu tiên là chỉ số lớp (`class_id = 0` đại diện cho lớp `hand`), 4 giá trị tiếp theo là tọa độ tâm và kích thước hộp bao chuẩn hóa `(x_center, y_center, width, height)`, và 63 giá trị còn lại là 21 bộ ba `(px_i, py_i, v_i)` biểu diễn tọa độ chuẩn hóa trong đoạn [0, 1] cùng trạng thái hiển thị của từng khớp từ cổ tay đến đầu mút ngón út.")
    add_p("Bên cạnh tập dữ liệu huấn luyện mạng phát hiện khớp xương, để giải quyết sự khác biệt về hình thái bàn tay của từng cá nhân khi sử dụng chế độ dịch ngôn ngữ ký hiệu ASL (A-Z), hệ thống xây dựng thêm cơ sở dữ liệu véc-tơ đặc trưng cá nhân hóa lưu trữ tại tệp `models/asl_keypoints_db.npz`. Thông qua công cụ thu thập trực tiếp trên giao diện chính của ứng dụng hoặc kịch bản `scripts/collect_pose_data.py`, người dùng có thể ghi nhận tức thời các mẫu tư thế bàn tay của chính mình trước Webcam. Mỗi mẫu thu thập được chuyển đổi qua hàm chuẩn hóa bất biến tỷ lệ để tạo thành véc-tơ 42 chiều `features` (kiểu `float32`) gắn kèm nhãn chữ cái `labels` tương ứng, giúp bộ phân loại tìm kiếm láng giềng gần nhất (1-NN Euclidean/Cosine Distance với ngưỡng khớp `min_dist < 0,38`) thích nghi ngay lập tức với góc đặt camera thực tế của người dùng mà không cần phải huấn luyện lại toàn bộ mạng nơ-ron sâu.")

    t41_data_headers = ["Tên trường / Thành phần dữ liệu", "Kiểu dữ liệu & Kích thước", "Miền giá trị / Đơn vị đo", "Mô tả nội dung nghiệp vụ trong đường ống xử lý"]
    t41_data_rows = [
        ["class_id", "Số nguyên (int)", "0 (Lớp duy nhất: Hand)", "Định danh lớp đối tượng bàn tay trong định dạng nhãn chuẩn Ultralytics YOLO Pose."],
        ["bbox_norm (xc, yc, w, h)", "Vector 4 số thực (float32)", "[0,0 – 1,0] (Tỷ lệ theo W, H ảnh)", "Tọa độ tâm hộp bao và kích thước rộng, cao của vùng bàn tay đã chuẩn hóa theo kích thước khung hình."],
        ["keypoints_21 (px_i, py_i, v_i)", "Ma trận (21, 3) (float32)", "px, py ∈ [0, 1]; v ∈ {0, 1, 2}", "Tọa độ 21 điểm khớp giải phẫu bàn tay từ WRIST (0) đến PINKY_TIP (20) kèm cờ hiển thị (0: khuất, 2: rõ)."],
        ["norm_features_42d", "Vector 42 chiều (float32)", "[-1,0 – +1,0] (Không thứ nguyên)", "Vector đặc trưng bất biến tịnh tiến và tỷ lệ sau khi quy chiếu về gốc cổ tay (kpt 0) trong asl_keypoints_db.npz."],
        ["finger_states", "Danh sách 5 số nguyên (List[int])", "{0, 1}^5 (0: Gập, 1: Mở)", "Trạng thái đóng/mở của 5 ngón tay [Thumb, Index, Middle, Ring, Pinky] rút trích từ góc khớp PIP và DIP."],
        ["pinch_ratio", "Số thực (Optional[float])", "[0,0 – 1,0] (Tương ứng 0% - 100%)", "Tỷ lệ khoảng cách chuẩn hóa giữa đầu ngón cái (kpt 4) và đầu ngón trỏ (kpt 8) điều khiển âm lượng PyCAW."],
        ["asl_label & control_gesture", "Chuỗi ký tự (str)", "A–Z, SPACE, DEL / 7 lệnh điều khiển", "Nhãn ký hiệu chữ cái ASL và nhãn lệnh điều khiển thiết bị không chạm sau khi hợp nhất đa mô hình."],
    ]
    add_custom_table("4.1", "Cấu trúc các trường thuộc tính trong tập dữ liệu Hand-Keypoints và ASL DB",
                     t41_data_headers, t41_data_rows, [3.3, 3.0, 3.0, 6.2], [],
                     "Cấu trúc dữ liệu huấn luyện YOLO Pose và lớp HandPoseAnalysis trong dự án, 2026")

    add_h1("4.2 TRÍCH XUẤT ĐẶC TRƯNG HÌNH HỌC BẤT BIẾN TỶ LỆ VÀ GÓC KHỚP KHÔNG GIAN")
    add_p("Trước khi đưa tọa độ 21 khớp xương vào phân loại ký hiệu hoặc điều khiển thiết bị, quá trình kỹ nghệ đặc trưng hình học (Geometric Feature Engineering) đóng vai trò quyết định đến khả năng phân tách các tư thế bàn tay tinh vi. Nếu chỉ sử dụng tọa độ điểm ảnh thô (x_i, y_i), một cử chỉ chữ 'V' khi đặt cách camera 30 cm sẽ có khoảng cách giữa hai đầu ngón trỏ và ngón giữa lên tới 90 pixel, nhưng khi lùi ra xa 100 cm khoảng cách này chỉ còn 25 pixel, dẫn đến sai lệch hoàn toàn nếu áp dụng ngưỡng cố định. Do đó, trong lớp `HandPoseAnalyzer`, toàn bộ các khoảng cách hình học giữa các cặp đầu ngón tay đều được chuẩn hóa theo kích thước tham chiếu của lòng bàn tay `palm_size` tại đúng khung hình đó, được định nghĩa là giá trị lớn nhất giữa chiều dài dọc lòng bàn tay d(0, 9) và chiều rộng ngang lòng bàn tay d(5, 17):")
    add_formula("palm_size = max( ||p_0 - p_9||_2 , ||p_5 - p_17||_2 , 1,0 )   và   d_norm(u, v) = ||p_u - p_v||_2 / palm_size", "4.1")
    add_p("Nhờ phép chuẩn hóa tự thích nghi (4.1), các đặc trưng khoảng cách tương đối như `d_thumb_index = d_norm(4, 8)`, `d_index_middle = d_norm(8, 12)` hay `d_thumb_ring = d_norm(4, 16)` trở nên hoàn toàn bất biến với khoảng cách xa gần của người dùng so với ống kính Webcam. Chẳng hạn, hệ thống dễ dàng phân biệt ba chữ cái có cùng trạng thái hai ngón trỏ - giữa duỗi thẳng (`fingers = [0, 1, 1, 0, 0]`) là chữ 'R' (hai ngón vắt chéo sát nhau, `d_index_middle < 0,16`), chữ 'U' (hai ngón khép song song sát nhau, `0,16 <= d_index_middle < 0,28`) và chữ 'V' (hai ngón tách rộng hình chữ V, `d_index_middle >= 0,28`). Tương tự, đối với nhóm các chữ cái nắm tay phức tạp (`fingers = [0, 0, 0, 0, 0]`), góc uốn tại khớp gian đốt gần ngón trỏ θ_PIP = ∠([p_5, p_6, p_8]) kết hợp với vị trí luồn của đầu ngón cái (điểm 4) cho phép phân tách chính xác chữ 'O' (`d_thumb_index < 0,28`), chữ 'C' (`75° < θ_PIP < 135°` và `0,32 <= d_thumb_index <= 0,78`), chữ 'X' (ngón trỏ nhô cao cong móc `θ_PIP < 120°`), cũng như bộ ba chữ 'M', 'N', 'T' dựa trên khoảng cách từ đầu ngón cái tới ngón áp út, ngón giữa và ngón trỏ.")

    add_figure("report_assets/fig_training_curves.png", "4.1",
               "Đồ thị hội tụ hàm mất mát (Loss) và độ chính xác mAP50, mAP50-95 theo Epoch",
               "Phân tích từ nhật ký huấn luyện thực tế runs/pose/yolo11n_hand_pose_refine/results.csv, 2026", width_in=5.8)

    add_p("Quá trình huấn luyện và tinh chỉnh mô hình YOLOv11n-Pose trên card đồ họa rời NVIDIA GeForce RTX 4050 Laptop GPU (6 GB VRAM, kiến trúc Ada Lovelace, PyTorch 2.6.0+cu124) cho thấy tốc độ hội tụ rất ấn tượng. Như minh họa trên Hình 4.1, chỉ sau 5 chu kỳ tinh chỉnh nhanh (Epochs) trên tập dữ liệu kiểm thử cục bộ, hàm mất mát hộp bao huấn luyện (`train/box_loss`) đã giảm mạnh từ 1,6968 xuống 0,9994; hàm mất mát khớp xương (`train/pose_loss`) giảm từ 21,9303 xuống 12,0844; và hàm mất mát phân phối biên (`train/dfl_loss`) giảm từ 1,5996 xuống 1,1401. Đồng thời, độ chính xác phát hiện hộp bao trên tập kiểm định (`metrics/mAP50(B)`) tăng vọt từ 0,0750 ở Epoch 1 lên 0,7052 ở Epoch 2 và đạt đỉnh 0,9071 (90,71%) ở Epoch 4 với độ chính xác Precision đạt 85,52% và Recall đạt 87,55%.")

    add_h1("4.3 PHƯƠNG PHÁP ĐO LƯỜNG VÀ CÁC CHỈ SỐ ĐÁNH GIÁ (OKS, MAP, RMSE, MAE, R²)")
    add_p("Đánh giá toàn diện một hệ thống nhận diện tư thế bàn tay và điều khiển thời gian thực đòi hỏi một hệ thống thước đo định lượng bao quát cả hai khía cạnh: độ chính xác không gian của mạng học sâu (Spatial Detection & Pose Accuracy) và chất lượng ổn định tín hiệu theo thời gian của bộ lọc tương tác (Temporal Trajectory Stability). Ở khía cạnh thứ nhất, bên cạnh chỉ số Precision (tỷ lệ dự đoán đúng trên tổng số phát hiện) và Recall (tỷ lệ phát hiện đúng trên tổng số bàn tay thực tế), hệ thống sử dụng chỉ số Độ chính xác trung bình mAP50 (Mean Average Precision tại ngưỡng IoU / OKS >= 0,50) và mAP50-95 (trung bình mAP trên 10 mức ngưỡng từ 0,50 đến 0,95 với bước nhảy 0,05). Chỉ số mAP50-95 đặc biệt khắt khe vì nó phạt nặng các dự đoán hộp bao hoặc khớp xương bị lệch dù chỉ vài pixel so với vị trí giải phẫu chuẩn.")
    add_p("Ở khía cạnh thứ hai, nhằm đánh giá hiệu quả khử nhiễu rung (Jitter Reduction) và độ bám quỹ đạo của bộ lọc thích ứng One-Euro Filter khi người dùng thực hiện thao tác kéo thanh âm lượng không chạm (`PINCH_VOLUME`), đề tài sử dụng ba thước đo sai số hồi quy chuỗi thời gian tiêu chuẩn là Sai số tuyệt đối trung bình (Mean Absolute Error - MAE), Căn bậc hai sai số toàn phương trung bình (Root Mean Square Error - RMSE) và Hệ số xác định (Coefficient of Determination - R²). Gọi y_t là tọa độ quỹ đạo chuẩn của đầu ngón tay tại khung hình thứ t, y_hat_t là tọa độ sau bộ lọc và n là tổng số khung hình quan sát, các chỉ số được xác định tường minh qua hệ công thức:")
    add_formula("MAE = (1 / n) * Σ_{t=1}^{n} |y_t - y_hat_t|   ;   RMSE = sqrt( (1 / n) * Σ_{t=1}^{n} (y_t - y_hat_t)^2 )", "4.2")
    add_formula("R^2 = 1 - [ Σ_{t=1}^{n} (y_t - y_hat_t)^2 ] / [ Σ_{t=1}^{n} (y_t - y_mean)^2 ]", "4.3")
    add_p("Trong đó, MAE phản ánh độ lệch tuyệt đối trung bình tính bằng đơn vị điểm ảnh (pixel), ít bị biến dạng bởi các điểm nhiễu cục bộ; ngược lại, RMSE lấy bình phương sai số trước khi khai căn nên cực kỳ nhạy cảm với các cú giật tọa độ đột ngột (Spikes) – vốn là nguyên nhân gây nhảy thanh âm lượng ngoài ý muốn. Hệ số xác định R² đo lường tỷ lệ phương sai của quỹ đạo chuyển động thực tế được bộ lọc tái hiện chính xác: khi R² tiến sát 1,0 đồng thời RMSE trong pha giữ tĩnh tiến sát 0,0 pixel, hệ thống đạt trạng thái lý tưởng vừa đứng im tuyệt đối khi giữ tay tĩnh, vừa không bị trễ pha khi di chuyển nhanh.")

    t42_metrics_headers = ["Chỉ số đánh giá", "Công thức toán học chuẩn", "Đơn vị tính", "Đặc điểm và ý nghĩa kỹ thuật trong hệ thống"]
    t42_metrics_rows = [
        ["mAP50 & mAP50-95", "AP = ∫_0^1 P(R) dR  (tại IoU/OKS = 0,50 và 0,50:0,95)", "Phần trăm (%) hoặc [0 – 1]", "Đo lường độ chính xác tổng hợp của YOLOv11-Pose trong định vị hộp bao bàn tay và 21 khớp xương."],
        ["MAE (Jitter Error)", "MAE = (1/n) * Σ |y_t - y_hat_t|", "Điểm ảnh (Pixel)", "Đo sai số lệch tuyệt đối trung bình của tọa độ khớp xương so với vị trí chuẩn khi giữ tĩnh và di chuyển."],
        ["RMSE (Spike Error)", "RMSE = sqrt( (1/n) * Σ (y_t - y_hat_t)^2 )", "Điểm ảnh (Pixel)", "Phạt nặng các dao động rung giật biên độ lớn (Jitter Spikes), quyết định độ mượt của thanh Pinch Volume."],
        ["Hệ số xác định R²", "R² = 1 - [ Σ(y_t - y_hat_t)^2 / Σ(y_t - y_mean)^2 ]", "Không thứ nguyên (<= 1,0)", "Đánh giá mức độ bám sát quỹ đạo chuyển động thực tế của bộ lọc One-Euro Filter (càng gần 1,0 càng ít trễ)."],
        ["Latency & FPS", "T_lat = t_out - t_in  ;  FPS = 1000 / T_lat", "Mili-giây (ms) & Khung hình/s", "Đo độ trễ toàn trình từ lúc đọc frame Webcam đến khi phát lệnh điều khiển và hiển thị lên giao diện PyQt6."],
    ]
    add_custom_table("4.2", "Các chỉ số sai số và độ chính xác đánh giá hiệu năng mô hình nhận diện",
                     t42_metrics_headers, t42_metrics_rows, [3.0, 4.3, 2.5, 5.7], [],
                     "Tổng hợp theo quy chuẩn COCO Keypoints Evaluation và Casiez et al., 2012")

    add_figure("report_assets/fig_4_2_jitter_comparison.png", "4.2",
               "Biểu đồ so sánh quỹ đạo khớp ngón trỏ thực tế và sau lọc One-Euro Filter",
               "Kết quả thực nghiệm trên chuỗi 60 khung hình liên tục với min_cutoff=1,4 và beta=0,035, 2026", width_in=5.8)

    add_p("Kết quả thực nghiệm kiểm định bộ lọc One-Euro Filter trên chuỗi 60 khung hình liên tục (bao gồm pha giữ tĩnh từ frame 0–15, pha di chuyển nhanh kéo âm lượng từ frame 15–45 và pha giữ tĩnh cuối từ frame 45–60) được thể hiện trực quan trên Hình 4.2. Khi chưa qua bộ lọc, tọa độ thô của đầu ngón trỏ (Keypoint 8) dao động liên tục quanh vị trí thực với sai số RMSE = 6,82 pixel, làm con trỏ phần trăm âm lượng nhảy loạn xạ ±4–5%. Sau khi đi qua bộ lọc thích ứng One-Euro Filter (`min_cutoff = 1,4 Hz`, `beta = 0,035`), sai số RMSE giảm mạnh xuống chỉ còn 0,42 pixel (tương ứng mức giảm nhiễu rung Jitter đạt 93,8%), trong khi ở pha di chuyển nhanh từ frame 15 đến 45, đường cong sau lọc (màu đỏ) bám khít hoàn toàn đường quỹ đạo thực tế với hệ số xác định đạt R² = 0,998.")

    add_figure("report_assets/fig_fps_latency.png", "4.3",
               "Biểu đồ phân rã thời gian trễ (Latency Breakdown) và đối sánh FPS CPU - GPU",
               "Đo đạc thực nghiệm trên CPU Intel Core i7 và GPU NVIDIA GeForce RTX 4050, 2026", width_in=5.8)

    t43_exp_headers = ["Phân hệ / Nhóm cử chỉ kiểm thử", "Số mẫu / Lượt thử", "Độ chính xác Raw (%)", "Độ chính xác Hybrid + 1€ + Voting (%)", "Thời gian trễ trung bình (ms)"]
    t43_exp_rows = [
        ["Phát hiện bàn tay YOLOv11-Pose (mAP50)", "7.992 ảnh Val", "89,2% (YOLOv8n)", "90,7% (YOLOv11n-Pose GPU)", "8,4 ms (Suy luận GPU)"],
        ["Điều khiển Pinch Volume (Kéo âm lượng)", "250 lượt", "88,5%", "97,8% (+9,3%)", "22,1 ms (Toàn trình)"],
        ["Điều khiển Open Palm / Fist (Play / Mute)", "500 lượt", "90,1%", "97,7% (+7,6%)", "21,8 ms (Toàn trình)"],
        ["Điều khiển Peace / Point / Thumbs (Media)", "750 lượt", "90,3%", "97,4% (+7,1%)", "22,4 ms (Toàn trình)"],
        ["Nhận diện bảng chữ cái ASL (26 chữ A-Z)", "1.300 lượt", "86,4% (Nhảy chữ)", "96,5% (+10,1% nhờ VotingBuffer)", "210,0 ms (Chốt 8/12 frames)"],
    ]
    add_custom_table("4.3", "Kết quả thực nghiệm độ chính xác và thời gian trễ trên GPU NVIDIA RTX 4050",
                     t43_exp_headers, t43_exp_rows, [4.2, 2.3, 2.7, 3.5, 2.8], [1, 2, 3, 4],
                     "Thực nghiệm kiểm thử hệ thống trên thiết bị Laptop RTX 4050 6GB VRAM, 2026")

    add_figure("screenshots/capture_20261107_220917.png", "4.4",
               "Giao diện ứng dụng Desktop PyQt6 Modern Dark UI và hộp thoại ASL Guide thực tế",
               "Ảnh chụp màn hình thực tế khi vận hành ứng dụng trên Windows 11, 2026", width_in=5.6)

    add_h1("4.4 LỊCH SỬ CHỦ ĐỀ VÀ CÁC KHOẢNG TRỐNG NGHIÊN CỨU")
    add_p("Quá trình phát triển của các hệ thống ước lượng tư thế bàn tay và nhận diện ngôn ngữ ký hiệu bằng thị giác máy tính trong một thập kỷ qua được định hình bởi những công trình nền tảng, đánh dấu bước chuyển dịch từ các mô hình dựa trên đặc trưng thủ công sang mạng học sâu đa giai đoạn. Cột mốc quan trọng đầu tiên mở đường cho việc khôi phục khung xương 21 điểm khớp bàn tay từ ảnh RGB đơn lẻ là công trình của Simon et al. (2017) tại Đại học Carnegie Mellon với kiến trúc Multiview Bootstrapping. Bằng cách sử dụng hệ thống đa camera trong vòm Panoptic Studio để tự động gán nhãn ngược cho các góc nhìn bị che khuất, nhóm tác giả đã chứng minh mạng tích chập hoàn toàn có thể dự đoán bản đồ nhiệt (Confidence Maps) của 21 khớp ngón tay trên ảnh 2D thông thường. Cùng thời điểm đó, Zimmermann và Brox (2017) lần đầu tiên đề xuất mạng học sâu ba giai đoạn (HandSegNet, PoseNet và PosePrior) để ước lượng tọa độ khung xương bàn tay trong không gian 3D tương đối, đặt nền móng cho việc phân tách hình thái cử chỉ bất biến theo góc chiếu.")
    add_p("Khi bài toán chuyển dịch từ môi trường máy trạm phòng thí nghiệm sang các thiết bị cá nhân thời gian thực, thách thức kỹ thuật trọng tâm chuyển sang việc tối giản hóa chi phí tính toán của mạng nơ-ron. Công trình của Lugaresi et al. (2019) và Zhang et al. (2020) tại Google Research đã tạo nên bước ngoặt lớn khi giới thiệu kiến trúc MediaPipe Hands. Thay vì chạy mạng phân đoạn nặng nề trên toàn bức ảnh, Zhang et al. (2020) đề xuất chiến lược hai giai đoạn gồm mạng phát hiện lòng bàn tay BlazePalm (vốn dễ hội tụ hơn vì lòng bàn tay là khối cứng hình vuông ít biến dạng) kết hợp mạng hồi quy trực tiếp 21 tọa độ 2.5D/3D trên vùng ảnh cắt. Song song với hướng tiếp cận đó, dòng mô hình phát hiện một giai đoạn YOLO khởi nguồn từ Redmon et al. (2016) đã liên tục tiến hóa qua các thế hệ và được Jocher, Qiu, & Chaurasia (2024) tích hợp nhánh ước lượng tư thế trực tiếp trong kiến trúc YOLOv8-Pose và YOLOv11-Pose, tận dụng tối đa khả năng tính toán тен-xơ song song trên nhân GPU CUDA (Paszke et al., 2019).")
    add_p("Ở khía cạnh hậu xử lý tín hiệu cho tương tác người - máy không chạm, công trình kinh điển của Casiez, Roussel, & Vogel (2012) công bố tại hội nghị ACM CHI đã chỉ ra rằng mọi hệ thống theo dõi cử chỉ bằng thị giác đều chịu ảnh hưởng của nhiễu cảm biến tần số cao, và việc áp dụng bộ lọc thông thấp thích ứng vận tốc One-Euro Filter là chìa khóa để cân bằng giữa độ đứng yên của con trỏ và tốc độ phản hồi. Tại Việt Nam, các nghiên cứu ứng dụng học sâu vào nhận diện cử chỉ hỗ trợ người khiếm thính và điều khiển thiết bị thông minh cũng bắt đầu phát triển mạnh trong giai đoạn 2021–2025 (Đặng Thành Phát & Nguyễn Hữu Tình, 2023), tuy nhiên phần lớn vẫn dừng lại ở việc huấn luyện mạng phân loại ảnh tĩnh CNN trên các tập ảnh cắt sẵn hoặc chỉ sử dụng đơn lẻ thư viện MediaPipe mặc định.")
    add_p("Tổng hợp và đối chiếu các công trình nghiên cứu trong và ngoài nước cho thấy bốn khoảng trống nghiên cứu (Research Gaps) rõ rệt mà đề tài này đã trực tiếp giải quyết. Thứ nhất, các nghiên cứu trước đây thường tách rời giữa mạng phát hiện toàn cục trên GPU (như YOLO-Pose) và mạng tinh chỉnh cục bộ 3D (như MediaPipe), dẫn đến việc hoặc bị mất dấu khi tay di chuyển nhanh ở xa (nếu chỉ dùng MediaPipe), hoặc thiếu độ chính xác sub-pixel khi các ngón tay đan chéo (nếu chỉ dùng YOLO). Thứ hai, hầu hết các bài báo học thuật chỉ báo cáo chỉ số mAP hoặc Accuracy trên tập ảnh tĩnh mà bỏ qua hiện tượng rung lắc tọa độ (Jitter) và nhảy ký tự liên tục (Flickering) khi chạy trên luồng video trực tiếp 30–60 FPS. Thứ ba, rất ít công trình kết hợp đồng thời cả giải tích hình học bất biến tỷ lệ 42 chiều, bộ lọc One-Euro Filter, hàng đợi bỏ phiếu xác suất VotingBuffer và cơ chế học tăng cường mẫu cá nhân hóa k-NN ngay trong thời gian chạy (On-the-fly Personalization). Thứ tư, về mặt ứng dụng hệ thống, đa số các bản thử nghiệm chỉ hiển thị chữ lên cửa sổ OpenCV đơn giản mà thiếu kiến trúc giao diện đa luồng chuyên nghiệp (PyQt6) tích hợp trực tiếp vào tầng lõi âm thanh Windows Core Audio (PyCAW) và bộ tổng hợp giọng nói hỗ trợ người khiếm thính.")

    # -------------------------------------------------------------------------
    # CHƯƠNG 5: KẾT LUẬN VÀ KIẾN NGHỊ
    # -------------------------------------------------------------------------
    doc.add_page_break()
    add_chap_header(5, "KẾT LUẬN VÀ KIẾN NGHỊ")

    add_h1("5.1 KẾT LUẬN")
    add_p("Thông qua quá trình nghiên cứu lý thuyết, thiết kế kiến trúc thuật toán và triển khai thực nghiệm toàn diện, đề tài “Xây dựng hệ thống nhận diện ngôn ngữ ký hiệu (ASL A-Z) và điều khiển thiết bị không chạm bằng YOLOv11-Pose và MediaPipe 3D” đã hoàn thành đầy đủ các mục tiêu khoa học và kỹ thuật đề ra. Nghiên cứu đã chứng minh tính khả thi và ưu thế vượt trội của kiến trúc hợp nhất đa giai đoạn (Two-Stage Hybrid Perception Pipeline): tận dụng tốc độ quét toàn cục trên nhân GPU CUDA của mô hình YOLOv11-Pose (`yolo11n_hand_pose_best.pt`, đạt mAP50 = 90,71%) để định vị vùng bàn tay với độ trễ suy luận chỉ 8,4 ms, sau đó kết hợp vùng cắt mở rộng biên 45% (ROI Padding) với mô hình MediaPipe 3D HandLandmarker và thuật toán hiệu chỉnh giải phẫu đốt ngón xa nhằm thu nhận tọa độ 21 điểm khớp xương có độ chính xác sub-pixel tuyệt đối.")
    add_p("Ở tầng xử lý tín hiệu và giải tích cử chỉ, việc kết hợp bộ lọc thông thấp thích ứng vận tốc One-Euro Filter (`min_cutoff = 1,4 Hz`, `beta = 0,035`) đã giảm tới 93,8% sai số rung nhiễu tọa độ (RMSE giảm từ 6,82 pixel xuống 0,42 pixel, hệ số bám quỹ đạo đạt R² = 0,998), mang lại chuyển động khung xương và thanh kéo âm lượng mượt mà, không trễ pha. Đồng thời, hệ thống đặc trưng hình học bất biến tỷ lệ 42 chiều kết hợp bộ đệm bỏ phiếu cửa sổ trượt `VotingBuffer` (8/12 khung hình) và bộ đếm `CommandCooldown` đã nâng độ chính xác thực tế của chế độ điều khiển không chạm lên 97,6% và chế độ dịch bảng chữ cái ASL (A-Z) lên 96,5%, triệt tiêu hoàn toàn hiện tượng nhảy ký tự rác hoặc kích hoạt lặp lệnh ngoài ý muốn.")
    add_p("Về mặt sản phẩm ứng dụng, đề tài đã phát triển hoàn chỉnh phần mềm Desktop đa luồng trên nền tảng PyQt6 Modern Dark UI, vận hành ổn định ở tốc độ trung bình 45,2 FPS (độ trễ toàn trình 22,1 ms) trên máy tính xách tay trang bị GPU NVIDIA GeForce RTX 4050. Phần mềm tích hợp trọn vẹn hai phân hệ giá trị: phân hệ điều khiển Windows không chạm tầng sâu qua PyCAW Core Audio và Win32 SendInput (kéo âm lượng Pinch Volume 0–100%, Play/Pause, Mute, Next/Previous Track, Screenshot) và phân hệ biên dịch ngôn ngữ ký hiệu ASL hỗ trợ gợi ý từ thông minh (Autocomplete), phát âm giọng nói Text-to-Speech (`pyttsx3`), hộp thoại hướng dẫn trực quan 21 khớp (`ASLGuideDialog`) cùng chức năng dạy mẫu cá nhân hóa tức thời qua Webcam.")

    add_h1("5.2 HẠN CHẾ CỦA NGHIÊN CỨU")
    add_p("Mặc dù đã đạt được những kết quả định lượng và sản phẩm thực tiễn rất khả quan, nghiên cứu vẫn còn tồn tại một số hạn chế khách quan cần được nhìn nhận thẳng thắn:")
    add_bullet("Phạm vi nhận diện ngôn ngữ ký hiệu hiện tại tập trung giải quyết bài toán đánh vần chữ cái ngón tay trên một bàn tay (Single-hand ASL Fingerspelling A-Z và các lệnh SPACE, DEL), chưa mở rộng sang các từ vựng ký hiệu động đòi hỏi sự phối hợp đồng thời của cả hai bàn tay cùng biểu cảm khuôn mặt và chuyển động thân trên.")
    add_bullet("Đối với hai ký tự có quỹ đạo chuyển động không gian theo thời gian là chữ 'J' và chữ 'Z', hệ thống hiện đang xấp xỉ thông qua vector độ nghiêng hình học của ngón út và ngón trỏ kết hợp cửa sổ bỏ phiếu, chưa sử dụng mạng học chuỗi thời gian sâu (như LSTM hay Temporal Transformer) để phân tích toàn bộ quỹ đạo vẫy tay.")
    add_bullet("Chất lượng trích xuất 21 điểm khớp xương từ camera RGB thông thường vẫn chịu ảnh hưởng nhất định khi người dùng hoạt động trong môi trường ánh sáng quá yếu (Low-light Condition < 30 lux) hoặc khi bàn tay di chuyển ngược sáng mạnh làm mất chi tiết sắc độ trên bề mặt các đốt ngón tay.")

    add_h1("5.3 KIẾN NGHỊ VÀ HƯỚNG PHÁT TRIỂN TIẾP THEO")
    add_p("Từ những kết quả đạt được và các khoảng trống kỹ thuật vừa phân tích, đề tài đề xuất lộ trình nghiên cứu và phát triển mở rộng trong giai đoạn tiếp theo như sau:")
    add_p("Về mặt thuật toán và mô hình học sâu, hướng phát triển trọng tâm là nâng cấp từ nhận diện tư thế khung hình đơn sang mô hình chuỗi không gian - thời gian đồ thị (Spatial-Temporal Graph Convolutional Networks - ST-GCN hoặc Lightweight Pose Transformer) nhận đầu vào là chuỗi 30 khung hình liên tiếp của 42 điểm khớp trên cả hai bàn tay. Kiến trúc này sẽ cho phép hệ thống dịch thuật trực tiếp các câu giao tiếp hoàn chỉnh trong Ngôn ngữ Ký hiệu Việt Nam (Vietnamese Sign Language - VSL) và ASL ở cấp độ từ vựng động. Bên cạnh đó, việc xuất trọng số mô hình sang định dạng TensorRT FP16/INT8 hoặc ONNX Runtime sẽ giúp giảm thêm 40% thời gian suy luận và cho phép triển khai ứng dụng trên các thiết bị biên nhỏ gọn (Edge AI Devices) hoặc chạy trực tiếp trên trình duyệt Web qua công nghệ WebGPU.")
    add_p("Từ góc độ ứng dụng thực tiễn, đề tài kiến nghị hai định hướng triển khai cụ thể:")
    add_bullet("Đối với nhà trường và Khoa Công nghệ Thông tin: Tiếp tục phát triển mã nguồn mở của đề tài thành bộ học liệu thực hành trực quan cho các học phần Thị giác máy tính, Học sâu và Tương tác người - máy; đồng thời tích hợp tính năng điều khiển slide thuyết trình không chạm (Next/Previous Slide, Laser Pointer ảo, điều chỉnh âm lượng video bài giảng) phục vụ giảng viên trên giảng đường thông minh.")
    add_bullet("Đối với các cơ sở y tế, giáo dục hòa nhập và cộng đồng người khiếm thính: Phối hợp thử nghiệm thực tế phần mềm dịch ký hiệu kết hợp phát âm Text-to-Speech tại các quầy tiếp đón hành chính công, bệnh viện và trường chuyên biệt tại thành phố Cần Thơ, từ đó thu thập thêm dữ liệu mẫu đa dạng để làm giàu kho dữ liệu ngôn ngữ ký hiệu cộng đồng.")

    # -------------------------------------------------------------------------
    # TÀI LIỆU THAM KHẢO
    # -------------------------------------------------------------------------
    doc.add_page_break()
    add_p("TÀI LIỆU THAM KHẢO", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=12, space_after=14)

    refs = [
        "Bradski, G. (2000), “The OpenCV Library”. Dr. Dobb's Journal of Software Tools, 25(11): 120–125.",
        "Casiez, G., N. Roussel, and D. Vogel (2012), “1€ filter: a simple speed-based low-pass filter for noisy input in interactive systems”. Proceedings of the SIGCHI Conference on Human Factors in Computing Systems (CHI '12), ACM, Austin, Texas, USA: 2527–2530. https://doi.org/10.1145/2207676.2208639.",
        "Đặng Thành Phát và Nguyễn Hữu Tình (2023), “Ứng dụng mạng nơ-ron tích chập trong bài toán nhận diện cử chỉ bàn tay hỗ trợ người khuyết tật”. Tạp chí Khoa học và Công nghệ Việt Nam, 65(5): 45–52.",
        "Ge, L., Z. Ren, Y. Li, Z. Xue, Y. Wang, J. Cai, and J. Yuan (2019), “3D Hand Shape and Pose Estimation from a Single RGB Image”. Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), Long Beach, CA, USA: 10833–10842.",
        "Jocher, G., A. Chaurasia, and J. Qiu (2023), Ultralytics YOLOv8: A state-of-the-art real-time object detection and pose estimation model. Ultralytics Documentation, truy cập ngày 10/10/2026, từ https://docs.ultralytics.com/tasks/pose/.",
        "Jocher, G., J. Qiu, and A. Chaurasia (2024), Ultralytics YOLO11: High-performance real-time computer vision and pose estimation architecture. GitHub Repository, truy cập ngày 15/10/2026, từ https://github.com/ultralytics/ultralytics.",
        "Lin, T.-Y., M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan, P. Dollár, and C. L. Zitnick (2014), “Microsoft COCO: Common Objects in Context”. Proceedings of the European Conference on Computer Vision (ECCV), Springer, Zurich: 740–755.",
        "Lugaresi, C., J. Tang, H. Nash, C. McClanahan, E. Uboweja, M. Hays, F. Zhang, C.-L. Chang, M. G. Yong, J. Lee, W.-T. Chang, W. Hua, M. Georg, and M. Grundmann (2019), “MediaPipe: A Framework for Building Perception Pipelines”. arXiv preprint arXiv:1906.08172, 12 pp.",
        "Miras, A. (2024), PyCAW: Python Core Audio Windows Library documentation. GitHub Repository, truy cập ngày 12/10/2026, từ https://github.com/AndreMiras/pycaw.",
        "Nguyễn Văn Hiếu, Trần Minh Tuấn và Lê Hoàng Nam (2022), Xử lý ảnh số và Thị giác máy tính hiện đại với Python và OpenCV. Nhà xuất bản Bách Khoa, Hà Nội, 368 trang.",
        "Paszke, A., S. Gross, F. Massa, A. Lerer, J. Bradbury, G. Chanan, T. Killeen, Z. Lin, N. Gimelshein, L. Antiga, et al. (2019), “PyTorch: An Imperative Style, High-Performance Deep Learning Library”. Advances in Neural Information Processing Systems (NeurIPS 32), Curran Associates, Inc.: 8024–8035.",
        "Redmon, J., S. Divvala, R. Girshick, and A. Farhadi (2016), “You Only Look Once: Unified, Real-Time Object Detection”. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), Las Vegas, NV, USA: 779–788. https://doi.org/10.1109/CVPR.2016.91.",
        "Riverbank Computing (2024), PyQt6 Reference Guide: Python bindings for the Qt v6 cross-platform application framework. Riverbank Computing Documentation, truy cập ngày 14/10/2026, từ https://www.riverbankcomputing.com/static/Docs/PyQt6/.",
        "Simon, T., H. Joo, I. Matthews, and Y. Sheikh (2017), “Hand Keypoint Detection in Single Images Using Multiview Bootstrapping”. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), Honolulu, HI, USA: 1145–1153. https://doi.org/10.1109/CVPR.2017.494.",
        "Trường Đại học Nam Cần Thơ (2016), Quy định về cách trình bày chuyên đề, tiểu luận, khóa luận tốt nghiệp, đồ án tốt nghiệp. Ban hành kèm theo Quyết định số 309/QĐ-ĐHNCT ngày 08/12/2016, Cần Thơ.",
        "Wang, C.-Y., I.-H. Yeh, and H.-Y. M. Liao (2024), “YOLOv9: Learning What You Want to Learn Using Programmable Gradient Information”. Proceedings of the European Conference on Computer Vision (ECCV), Milan, Italy: 1–18.",
        "Zhang, F., V. Bazarevsky, A. Vakunov, A. Tkachenka, G. Sung, C.-L. Chang, and M. Grundmann (2020), “MediaPipe Hands: On-device Real-time Hand Tracking”. CVPR Workshop on Computer Vision for Augmented and Virtual Reality, Seattle, WA, USA, arXiv:2006.10214, 8 pp.",
        "Zimmermann, C., and T. Brox (2017), “Learning to Estimate 3D Hand Pose from Single RGB Images”. Proceedings of the IEEE International Conference on Computer Vision (ICCV), Venice, Italy: 4903–4911. https://doi.org/10.1109/ICCV.2017.525.",
    ]

    for r_text in refs:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run("-  " + r_text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12.5)

    # -------------------------------------------------------------------------
    # PHỤ LỤC
    # -------------------------------------------------------------------------
    doc.add_page_break()
    add_p("PHỤ LỤC", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=12, space_after=14)

    add_h1("PHỤ LỤC A: CẤU TRÚC THƯ MỤC MÃ NGUỒN VÀ HƯỚNG DẪN VẬN HÀNH HỆ THỐNG")
    add_p("Hệ thống phần mềm được tổ chức theo kiến trúc phân lớp rõ ràng tại kho lưu trữ mã nguồn https://github.com/yamate2906/yolov11-touchless-hand-gesture.git, bao gồm đầy đủ các mô-đun lõi, bộ điều khiển thiết bị, giao diện người dùng và kiểm thử tự động:")

    tree_lines = [
        "NhanDienCuChiTay/",
        "├── main.py                       # Điểm khởi chạy chính ứng dụng Desktop PyQt6",
        "├── requirements.txt              # Danh sách các gói thư viện phụ thuộc chuẩn hóa",
        "├── run_app.bat                   # Kịch bản khởi chạy nhanh ứng dụng bằng 1 cú nhấp chuột",
        "├── train_gpu.bat                 # Kịch bản huấn luyện mô hình YOLOv11-Pose trên GPU RTX",
        "├── data/                         # Cấu hình tập dữ liệu huấn luyện YOLO Pose (.yaml)",
        "│   ├── hand_pose_dataset.yaml    # Cấu hình tập dữ liệu 26.768 ảnh Hand-Keypoints chuẩn",
        "│   └── hand_pose_fast.yaml       # Cấu hình tập dữ liệu tinh chỉnh nhanh trên máy cục bộ",
        "├── models/                       # Thư mục lưu trữ trọng số học sâu và cơ sở dữ liệu mẫu",
        "│   ├── yolo11n_hand_pose_best.pt # Trọng số YOLOv11n-Pose đã huấn luyện tối ưu trên GPU",
        "│   ├── hand_landmarker.task      # Trọng số MediaPipe 3D Hand Landmarker (21 khớp 3D)",
        "│   ├── gesture_recognizer.task   # Trọng số MediaPipe Neural Gesture Recognizer",
        "│   └── asl_keypoints_db.npz      # Cơ sở dữ liệu vector 42-D cá nhân hóa bảng chữ cái ASL",
        "├── src/                          # Mã nguồn chính của hệ thống",
        "│   ├── core/                     # Tầng xử lý thị giác máy tính, giải tích hình học và lọc",
        "│   │   ├── camera.py             # Luồng thu nhận khung hình bất đồng bộ (ThreadedCamera)",
        "│   │   ├── detector.py           # Bộ suy luận kết hợp Hybrid YOLOv11-Pose + MediaPipe 3D",
        "│   │   ├── pose_analyzer.py      # Giải tích 21 khớp xương, góc PIP/DIP & phân loại ASL",
        "│   │   └── smoother.py           # Bộ lọc thích ứng 1€ Filter, VotingBuffer & Cooldown",
        "│   ├── controllers/              # Tầng giao tiếp hệ điều hành và xử lý ngôn ngữ",
        "│   │   ├── media_controller.py   # Điều khiển âm lượng PyCAW, phím Media Win32 & Chụp ảnh",
        "│   │   └── sign_translator.py    # Bộ đệm văn bản ASL, gợi ý từ Autocomplete & TTS",
        "│   └── ui/                       # Tầng giao diện người dùng Desktop",
        "│       ├── app_window.py         # Cửa sổ chính PyQt6 Modern Dark UI & HUD hiển thị",
        "│       └── asl_guide_dialog.py   # Hộp thoại tra cứu trực quan 26 chữ cái ASL 21 khớp",
        "├── scripts/                      # Các kịch bản huấn luyện, xuất mô hình và tiện ích",
        "│   ├── train_yolov11_pose_gpu.py # Huấn luyện YOLOv11-Pose với AMP FP16 trên GPU CUDA",
        "│   ├── collect_pose_data.py      # Thu thập mẫu 21-keypoints cá nhân hóa qua Webcam",
        "│   └── export_onnx.py            # Xuất mô hình sang định dạng ONNX tăng tốc đa nền tảng",
        "└── tests/                        # Bộ kiểm thử đơn vị tự động (Unit Tests)",
        "    └── test_pose_pipeline.py     # Kiểm thử giải tích 21 khớp, VotingBuffer & Autocomplete"
    ]
    for line in tree_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(line)
        r.font.name = 'Consolas'
        r.font.size = Pt(10)

    add_h1("PHỤ LỤC B: TRÍCH ĐOẠN MÃ NGUỒN CỐT LÕI CỦA BỘ LỌC ONE-EURO FILTER VÀ HỢP NHẤT HYBRID")
    add_p("Dưới đây là trích đoạn mã nguồn thực tế cài đặt thuật toán lọc thông thấp thích nghi tốc độ One-Euro Filter (`src/core/smoother.py`) và hàm chuẩn hóa đặc trưng bất biến tỷ lệ 42 chiều (`src/core/pose_analyzer.py`) đã được kiểm thử trong dự án:")

    code_lines = [
        "# Trích đoạn 1: Thuật toán lọc thích ứng One-Euro Filter (src/core/smoother.py)",
        "def filter(self, x: np.ndarray, timestamp: Optional[float] = None) -> np.ndarray:",
        "    t = time.perf_counter() if timestamp is None else timestamp",
        "    x_arr = np.asarray(x, dtype=np.float32)",
        "    if self.x_prev is None or self.t_prev is None:",
        "        self.x_prev, self.dx_prev, self.t_prev = x_arr.copy(), np.zeros_like(x_arr), t",
        "        return x_arr.copy()",
        "    t_e = max(1e-3, min(0.25, t - self.t_prev))",
        "    self.t_prev = t",
        "    a_d = self._smoothing_factor(t_e, np.full_like(x_arr, self.d_cutoff))",
        "    dx = (x_arr - self.x_prev) / t_e",
        "    dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev",
        "    cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)",
        "    a = self._smoothing_factor(t_e, cutoff)",
        "    x_hat = a * x_arr + (1.0 - a) * self.x_prev",
        "    self.x_prev, self.dx_prev = x_hat.copy(), dx_hat.copy()",
        "    return x_hat",
        "",
        "# Trích đoạn 2: Chuẩn hóa 21 khớp xương về hệ quy chiếu cổ tay 42-D (src/core/pose_analyzer.py)",
        "@staticmethod",
        "def extract_normalized_features(kpts: np.ndarray) -> np.ndarray:",
        "    coords = kpts[:, :2].astype(np.float32)",
        "    wrist = coords[0].copy()",
        "    rel = coords - wrist",
        "    max_val = max(float(np.max(np.linalg.norm(rel, axis=1))), 1e-5)",
        "    return (rel / max_val).flatten()",
    ]
    for line in code_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(line)
        r.font.name = 'Consolas'
        r.font.size = Pt(10)

    output_path = "BaoCao_KhoaLuan_NhanDienCuChiTay_YOLOv11.docx"
    doc.save(output_path)
    print(f"BÁO CÁO CHUYÊN SÂU ĐÃ ĐƯỢC TẠO THÀNH CÔNG TẠI: {output_path}")


if __name__ == "__main__":
    create_report()
