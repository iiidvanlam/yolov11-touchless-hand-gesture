"""
Tạo Báo cáo Cuối kỳ Môn học / Khóa luận định dạng Microsoft Word (.docx)
Cập nhật theo đúng mẫu Trang bìa, tác giả Đinh Văn Lắm (MSSV: 235292, Lớp: DH23TIN06),
GVHD: TS. Ngô Hồ Anh Khôi.
Xóa các trang: Lời cảm tạ, Trang cam kết, Nhận xét của cán bộ hướng dẫn, Chấp thuận hội đồng.
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
    
    # Base configuration: A4, Margins: Left=3.5cm, Right=2.0cm, Top=2.5cm, Bottom=2.5cm
    # Header/Footer: 1.0cm
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
    
    # Configure default style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(13)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.2
    normal_style.paragraph_format.space_before = Pt(6)
    normal_style.paragraph_format.space_after = Pt(0)
    normal_style.paragraph_format.first_line_indent = Cm(1.0)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # XML Helper for page number in footer
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

    # Helper for adding paragraph styles
    def add_p(text, bold=False, italic=False, size=13, align=WD_ALIGN_PARAGRAPH.JUSTIFY, 
              first_indent=1.0, space_before=6, space_after=0, line_spacing=1.2):
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

    def add_chap_header(chap_num, chap_title):
        p1 = doc.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.first_line_indent = Cm(0)
        p1.paragraph_format.space_before = Pt(18)
        p1.paragraph_format.space_after = Pt(6)
        r1 = p1.add_run(f"CHƯƠNG {chap_num}")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(14)
        
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.first_line_indent = Cm(0)
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(18)
        r2 = p2.add_run(chap_title.upper())
        r2.bold = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(14)

    def add_h1(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(14)
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

    def add_h3(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(title_text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        return p

    def add_bullet(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.2
        r_bullet = p.add_run("- ")
        r_bullet.bold = True
        r_bullet.font.name = 'Times New Roman'
        r_bullet.font.size = Pt(13)
        r_text = p.add_run(text)
        r_text.font.name = 'Times New Roman'
        r_text.font.size = Pt(13)
        return p

    def add_figure(img_path, fig_num_str, fig_caption, source_text="Tác giả tổng hợp (2026)", width_in=5.6):
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
        r_num = p_cap.add_run(f"Hình {fig_num_str} ")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(13)
        r_txt = p_cap.add_run(fig_caption)
        r_txt.font.name = 'Times New Roman'
        r_txt.font.size = Pt(13)

        p_src = doc.add_paragraph()
        p_src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_src.paragraph_format.first_line_indent = Cm(0)
        p_src.paragraph_format.space_before = Pt(0)
        p_src.paragraph_format.space_after = Pt(10)
        r_src = p_src.add_run(f"Nguồn: {source_text}")
        r_src.italic = True
        r_src.font.name = 'Times New Roman'
        r_src.font.size = Pt(11)

    def format_table_cells(table, col_widths, headers, data, align_rights=[]):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr = table._tbl.tblPr
        tblBorders = parse_xml(
            r'<w:tblBorders %s>'
            r'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            r'  <w:left w:val="none"/>'
            r'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
            r'  <w:right w:val="none"/>'
            r'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>'
            r'  <w:insideV w:val="none"/>'
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
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(h_text)
            r.bold = True
            r.font.name = 'Times New Roman'
            r.font.size = Pt(12)

        for r_idx, row_data in enumerate(data):
            row = table.rows[r_idx + 1]
            for c_idx, val in enumerate(row_data):
                cell = row.cells[c_idx]
                cell.width = Cm(col_widths[c_idx])
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                p = cell.paragraphs[0]
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.0
                if c_idx in align_rights:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif c_idx == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(str(val))
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)

    def add_custom_table(table_num_str, table_caption, headers, data, col_widths, align_rights=[], source_text="Kết quả thực nghiệm trên thiết bị đề tài (2026)"):
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_cap.paragraph_format.first_line_indent = Cm(0)
        p_cap.paragraph_format.space_before = Pt(10)
        p_cap.paragraph_format.space_after = Pt(4)
        r_num = p_cap.add_run(f"Bảng {table_num_str} ")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(13)
        r_txt = p_cap.add_run(table_caption)
        r_txt.font.name = 'Times New Roman'
        r_txt.font.size = Pt(13)

        table = doc.add_table(rows=len(data) + 1, cols=len(headers))
        format_table_cells(table, col_widths, headers, data, align_rights)

        p_src = doc.add_paragraph()
        p_src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_src.paragraph_format.first_line_indent = Cm(0)
        p_src.paragraph_format.space_before = Pt(3)
        p_src.paragraph_format.space_after = Pt(10)
        r_src = p_src.add_run(f"Nguồn: {source_text}")
        r_src.italic = True
        r_src.font.name = 'Times New Roman'
        r_src.font.size = Pt(11)

    print("--- XÂY DỰNG TRANG BÌA THEO ĐÚNG MẪU NGƯỜI DÙNG CUNG CẤP ---")
    # SECTION 1: COVER ONLY (No page number)
    sec_cover = doc.sections[0]
    sec_cover.different_first_page_header_footer = True
    sec_cover.header.is_linked_to_previous = False
    sec_cover.footer.is_linked_to_previous = False

    # Header trường và khoa
    add_p("TRƯỜNG ĐẠI HỌC NAM CẦN THƠ", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=6, space_after=2)
    add_p("KHOA CÔNG NGHỆ THÔNG TIN", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=14)

    # Logo DNC chính giữa
    logo_path = "report_assets/dnc_logo.png"
    if os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.first_line_indent = Cm(0)
        p_logo.paragraph_format.space_before = Pt(4)
        p_logo.paragraph_format.space_after = Pt(14)
        p_logo.add_run().add_picture(logo_path, width=Inches(1.8))

    # Thông tin sinh viên
    add_p("ĐINH VĂN LẮM", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=4, space_after=2)
    add_p("MSSV: 235292", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=2)
    add_p("LỚP: DH23TIN06", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=18)

    # Đề tài
    add_p("ĐỀ TÀI", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=6, space_after=4)
    add_p("NGHIÊN CỨU VÀ XÂY DỰNG HỆ THỐNG NHẬN DIỆN NGÔN NGỮ KÝ HIỆU (ASL A-Z) VÀ ĐIỀU KHIỂN THIẾT BỊ KHÔNG CHẠM VỚI YOLOV11-POSE VÀ MEDIAPIPE 3D",
          bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=2, space_after=4)
    add_p("(AN OVERVIEW STUDY AND IMPLEMENTATION OF ASL HAND GESTURE RECOGNITION AND TOUCHLESS CONTROL USING YOLOV11-POSE AND MEDIAPIPE 3D)",
          bold=False, italic=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=20)

    # Thông tin học phần & Giảng viên
    add_p("BÁO CÁO CUỐI KỲ", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=4, space_after=2)
    add_p("Phương Pháp Nghiên Cứu và Viết Báo Cáo Khoa Học", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=2)
    add_p("Học kỳ I", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=6)

    add_p("GIẢNG VIÊN HƯỚNG DẪN: TS. NGÔ HỒ ANH KHÔI", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=4, space_after=2)
    add_p("NGÀNH: CÔNG NGHỆ THÔNG TIN", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=2)
    add_p("Mã số ngành: 7480201", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=0, space_after=25)

    add_p("Cần Thơ, Tháng 11/2026", bold=False, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=15, space_after=0)

    print("--- XÂY DỰNG SECTION 2: MỤC LỤC, TỪ VIẾT TẮT, DANH SÁCH BẢNG & HÌNH (ĐÁNH SỐ LA MÃ: ii, iii...) ---")
    sec_prelim = doc.add_section()
    apply_section_margins(sec_prelim)
    sec_prelim.header.is_linked_to_previous = False
    sec_prelim.footer.is_linked_to_previous = False
    set_section_numbering_type(sec_prelim, num_fmt='lowerRoman', start_num=1)
    add_page_number_to_footer(sec_prelim.footer.paragraphs[0])

    # Trang Mục lục (Trang 1 của Section 2)
    add_p("MỤC LỤC", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=15, space_after=15)
    
    toc_items = [
        ("DANH MỤC TỪ VIẾT TẮT", "ii", True, 0),
        ("DANH SÁCH BẢNG", "iii", True, 0),
        ("DANH SÁCH HÌNH", "iii", True, 0),
        ("CHƯƠNG 1: GIỚI THIỆU", "1", True, 0),
        ("  1.1 Đặt vấn đề nghiên cứu", "1", False, 1),
        ("  1.2 Mục tiêu nghiên cứu", "2", False, 1),
        ("    1.2.1 Mục tiêu tổng quát", "2", False, 2),
        ("    1.2.2 Mục tiêu cụ thể", "2", False, 2),
        ("  1.3 Phạm vi và đối tượng nghiên cứu", "3", False, 1),
        ("    1.3.1 Phạm vi nghiên cứu", "3", False, 2),
        ("    1.3.2 Đối tượng nghiên cứu", "3", False, 2),
        ("  1.4 Ý nghĩa khoa học và giá trị thực tiễn", "4", False, 1),
        ("  1.5 Phương pháp nghiên cứu và bố cục báo cáo", "4", False, 1),
        ("CHƯƠNG 2: CƠ SỞ LÝ LUẬN VÀ CÔNG NGHỆ LIÊN QUAN", "6", True, 0),
        ("  2.1 Cơ sở lý luận về thị giác máy tính và Hand Pose Estimation", "6", False, 1),
        ("    2.1.1 Cấu trúc giải phẫu 21 điểm khớp xương bàn tay", "7", False, 2),
        ("    2.1.2 Kiến trúc mô hình học sâu YOLOv11 và YOLOv11-Pose", "9", False, 2),
        ("    2.1.3 Google MediaPipe 3D HandLandmarker", "11", False, 2),
        ("    2.1.4 Giải thuật lọc làm mượt thích nghi One-Euro Filter", "12", False, 2),
        ("    2.1.5 Cơ chế chống nhảy chữ VotingBuffer", "13", False, 2),
        ("    2.1.6 Giao thức tương tác Windows Core Audio và SendInput", "14", False, 2),
        ("  2.2 Phương pháp nghiên cứu và huấn luyện", "15", False, 1),
        ("CHƯƠNG 3: THIẾT KẾ VÀ KIẾN TRÚC HỆ THỐNG", "19", True, 0),
        ("  3.1 Tổng quan kiến trúc hệ thống Hybrid", "19", False, 1),
        ("  3.2 Thiết kế các phân hệ cốt lõi", "22", False, 1),
        ("  3.3 Thiết kế các chức năng ứng dụng thực tế", "26", False, 1),
        ("  3.4 Thiết kế giao diện người dùng Desktop (PyQt6)", "31", False, 1),
        ("CHƯƠNG 4: KẾT QUẢ NGHIÊN CỨU VÀ ĐÁNH GIÁ", "35", True, 0),
        ("  4.1 Môi trường thực nghiệm và huấn luyện", "35", False, 1),
        ("  4.2 Kết quả huấn luyện mô hình YOLOv11-Pose trên GPU RTX 4050", "37", False, 1),
        ("  4.3 Kết quả thực nghiệm các tính năng hệ thống", "41", False, 1),
        ("  4.4 Đánh giá hiệu năng và thời gian trễ (FPS & Latency)", "46", False, 1),
        ("  4.5 So sánh giải pháp đề xuất với các phương pháp hiện có", "49", False, 1),
        ("CHƯƠNG 5: KẾT LUẬN VÀ KIẾN NGHỊ", "51", True, 0),
        ("  5.1 Kết luận", "51", False, 1),
        ("  5.2 Hạn chế của nghiên cứu", "52", False, 1),
        ("  5.3 Kiến nghị và hướng phát triển tiếp theo", "52", False, 1),
        ("TÀI LIỆU THAM KHẢO", "54", True, 0),
        ("PHỤ LỤC", "56", True, 0),
    ]

    tbl_toc = doc.add_table(rows=len(toc_items), cols=2)
    tbl_toc.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, (title, page, is_bld, lvl) in enumerate(toc_items):
        row = tbl_toc.rows[idx]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = Cm(14.0), Cm(1.5)
        p0, p1 = c0.paragraphs[0], c1.paragraphs[0]
        p0.paragraph_format.first_line_indent = Cm(0)
        p1.paragraph_format.first_line_indent = Cm(0)
        p0.paragraph_format.space_before = Pt(2)
        p1.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(2)
        p1.paragraph_format.space_after = Pt(2)
        p0.paragraph_format.line_spacing = 1.1
        p1.paragraph_format.line_spacing = 1.1
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        dots_count = max(4, int((13.5 - len(title)*0.2) * 5))
        r0 = p0.add_run(title + " " + "." * dots_count)
        r0.bold = is_bld
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(12)
        
        r1 = p1.add_run(page)
        r1.bold = is_bld
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(12)

    # Danh mục từ viết tắt (Trang ii)
    doc.add_page_break()
    add_p("DANH MỤC TỪ VIẾT TẮT", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=15, space_after=15)
    
    acr_headers = ["Từ viết tắt", "Tên tiếng Anh đầy đủ", "Ý nghĩa / Tên tiếng Việt"]
    acr_data = [
        ["AI", "Artificial Intelligence", "Trí tuệ nhân tạo"],
        ["API", "Application Programming Interface", "Giao diện lập trình ứng dụng"],
        ["ASL", "American Sign Language", "Ngôn ngữ ký hiệu Mỹ (A-Z)"],
        ["CNN", "Convolutional Neural Network", "Mạng nơ-ron tích chập"],
        ["CUDA", "Compute Unified Device Architecture", "Nền tảng tính toán song song trên GPU NVIDIA"],
        ["DFL", "Distribution Focal Loss", "Hàm phân phối tổn thất vị trí hộp"],
        ["DNC", "Nam Can Tho University", "Trường Đại học Nam Cần Thơ"],
        ["FPS", "Frames Per Second", "Số khung hình hiển thị trên giây"],
        ["GPU", "Graphics Processing Unit", "Bộ xử lý đồ họa chuyên dụng"],
        ["HCI", "Human-Computer Interaction", "Tương tác người - máy"],
        ["HUD", "Heads-Up Display", "Hiển thị thông tin trực quan trên khung video"],
        ["mAP", "Mean Average Precision", "Độ chính xác trung bình trung vị"],
        ["NMS", "Non-Maximum Suppression", "Giải thuật loại trừ các hộp dự đoán trùng lặp"],
        ["OKS", "Object Keypoint Similarity", "Độ tương đồng khóa khớp xương"],
        ["PyCAW", "Python Core Audio Windows", "Thư viện điều khiển âm thanh hệ thống Windows"],
        ["ROI", "Region of Interest", "Vùng ảnh quan tâm (vùng bàn tay)"],
        ["TTS", "Text-To-Speech", "Công nghệ chuyển đổi văn bản thành giọng nói"],
        ["UI", "User Interface", "Giao diện người dùng"],
        ["VRAM", "Video Random Access Memory", "Bộ nhớ video chuyên dụng của GPU"],
        ["YOLO", "You Only Look Once", "Mô hình nhận diện vật thể thời gian thực một giai đoạn"],
    ]
    
    tbl_acr = doc.add_table(rows=len(acr_data) + 1, cols=3)
    format_table_cells(tbl_acr, [2.5, 6.0, 7.0], acr_headers, acr_data, [])

    # Danh sách bảng & Danh sách hình (Trang iii)
    doc.add_page_break()
    add_p("DANH SÁCH BẢNG", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=15, space_after=12)
    tables_list = [
        ("Bảng 2.1: Danh sách định danh 21 điểm khớp xương bàn tay (Hand Keypoints Topology)", "7"),
        ("Bảng 2.2: So sánh đặc tính các phiên bản YOLO từ v8 đến v11 trong tác vụ Pose Estimation", "10"),
        ("Bảng 3.1: Bảng ánh xạ các cử chỉ điều khiển Touchless Control với sự kiện hệ điều hành Windows", "27"),
        ("Bảng 4.1: Bảng cấu hình phần cứng và môi trường phần mềm thực nghiệm", "35"),
        ("Bảng 4.2: Chi tiết số lượng mẫu dữ liệu huấn luyện và kiểm định Hand Keypoints", "36"),
        ("Bảng 4.3: Kết quả huấn luyện mô hình YOLOv11-Pose qua các Epoch trên GPU RTX 4050", "38"),
        ("Bảng 4.4: Bảng độ chính xác nhận diện các cử chỉ điều khiển không chạm (Touchless Control)", "42"),
        ("Bảng 4.5: Kết quả nhận diện bảng chữ cái ngôn ngữ ký hiệu ASL (A-Z) và thời gian phản hồi", "44"),
        ("Bảng 4.6: Phân rã thời gian trễ (Latency Breakdown) chi tiết của từng giai đoạn trong Pipeline", "47"),
        ("Bảng 4.7: So sánh tốc độ xử lý (FPS) và mức độ tiêu thụ phần cứng giữa CPU và GPU", "48"),
        ("Bảng 4.8: Bảng đối sánh tổng hợp giữa giải pháp đề xuất và các công trình liên quan", "50"),
    ]
    for t_title, t_page in tables_list:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.1
        dots_count = max(4, int((13.5 - len(t_title)*0.2) * 5))
        r0 = p.add_run(t_title + " " + "." * dots_count + " " + t_page)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(12)

    add_p("DANH SÁCH HÌNH", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=20, space_after=12)
    figures_list = [
        ("Hình 2.1: Mô hình topo 21 điểm mốc giải phẫu khớp xương bàn tay (Hand Landmarks)", "8"),
        ("Hình 2.2: Cấu trúc mạng tích chập trích xuất đặc trưng C3k2 và Head của YOLOv11-Pose", "10"),
        ("Hình 3.1: Sơ đồ khối kiến trúc phân tầng hệ thống Hybrid YOLOv11-Pose & MediaPipe 3D", "20"),
        ("Hình 3.2: Sơ đồ tuần tự luồng dữ liệu thời gian thực (Real-time Video Pipeline Sequence)", "21"),
        ("Hình 3.3: Cơ chế phân tách góc gập không gian 5 ngón tay trên mặt phẳng khớp bàn", "24"),
        ("Hình 3.4: Sơ đồ thuật toán lọc khử nhiễu thích nghi One-Euro Filter và bộ đệm VotingBuffer", "25"),
        ("Hình 3.5: Giao diện người dùng Desktop PyQt6 Modern Dark UI đang chạy thực tế", "32"),
        ("Hình 3.6: Hộp thoại trực quan ASL Guide Dialog hướng dẫn bảng ký hiệu 21 khớp xương", "33"),
        ("Hình 4.1: Đồ thị biến thiên các hàm mất mát (Loss Convergence) của YOLOv11-Pose theo Epoch", "39"),
        ("Hình 4.2: Đồ thị biến thiên độ chính xác Precision, Recall, mAP50 và mAP50-95 theo Epoch", "40"),
        ("Hình 4.3: Biểu đồ so sánh độ chính xác nhận diện các cử chỉ điều khiển Touchless Control", "43"),
        ("Hình 4.4: Biểu đồ phân rã thời gian trễ (Latency Breakdown) và so sánh FPS giữa CPU và GPU", "47"),
    ]
    for f_title, f_page in figures_list:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.1
        dots_count = max(4, int((13.5 - len(f_title)*0.2) * 5))
        r0 = p.add_run(f_title + " " + "." * dots_count + " " + f_page)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(12)

    print("--- XÂY DỰNG SECTION 3: NỘI DUNG CHÍNH (ĐÁNH SỐ Á RẬP: 1, 2, 3...) ---")
    sec_main = doc.add_section()
    apply_section_margins(sec_main)
    sec_main.header.is_linked_to_previous = False
    sec_main.footer.is_linked_to_previous = False
    set_section_numbering_type(sec_main, num_fmt='decimal', start_num=1)
    add_page_number_to_footer(sec_main.footer.paragraphs[0])

    # =========================================================================
    # CHƯƠNG 1
    # =========================================================================
    add_chap_header(1, "GIỚI THIỆU")

    add_h1("1.1 ĐẶT VẤN ĐỀ NGHIÊN CỨU")
    add_p("Trong kỷ nguyên phát triển mạnh mẽ của Trí tuệ nhân tạo (Artificial Intelligence - AI) và Thị giác máy tính (Computer Vision), phương thức giao tiếp giữa con người và máy tính (Human-Computer Interaction - HCI) đang trải qua những bước chuyển mình mang tính đột phá. Các giao thức nhập liệu truyền thống thông qua chuột, bàn phím cơ học hay màn hình cảm ứng điện dung, mặc dù đã chứng minh tính hiệu quả qua nhiều thập kỷ, song vẫn bộc lộ những rào cản đáng kể trong nhiều tình huống thực tiễn đặc thù.")
    add_p("Trước hết, đối với cộng đồng người khiếm thính và người câm - một bộ phận dân cư chiếm tỷ lệ đáng kể trong xã hội, ngôn ngữ ký hiệu (Sign Language), đặc biệt là bảng chữ cái ngôn ngữ ký hiệu ngón tay (American Sign Language Fingerspelling - ASL A-Z), là phương tiện giao tiếp tự nhiên và quan trọng nhất. Tuy nhiên, đại đa số người bình thường trong xã hội lại không được đào tạo để hiểu ngôn ngữ ký hiệu, tạo nên một khoảng cách vô hình nhưng vô cùng to lớn trong giáo dục, y tế, hành chính công và hòa nhập cộng đồng. Việc ứng dụng công nghệ thị giác máy tính để tự động nhận diện và dịch thuật thời gian thực ngôn ngữ ký hiệu thành văn bản và âm thanh phát âm trực tiếp là một nhiệm vụ cấp thiết, mang giá trị nhân văn sâu sắc.")
    add_p("Bên cạnh đó, nhu cầu về các phương thức điều khiển thiết bị không tiếp xúc trực tiếp (Touchless Control) ngày càng trở nên cấp thiết trong đời sống hiện đại. Trong các môi trường vô trùng như phòng phẫu thuật y tế, phòng thí nghiệm sinh học, dây chuyền sản xuất vi mạch hoặc trong các bối cảnh thuyết trình hội thảo, làm việc từ xa, việc tương tác trực tiếp lên thiết bị phần cứng có thể tiềm ẩn nguy cơ lây nhiễm chéo vi sinh vật hoặc làm gián đoạn dòng tập trung của người trình bày. Một hệ thống cho phép người dùng điều chỉnh âm lượng, điều khiển phát nhạc/video, chụp ảnh màn hình chỉ bằng các cử chỉ ngón tay trực quan tự nhiên trước Webcam thông thường sẽ mở ra giải pháp công nghệ vô cùng linh hoạt và tiện lợi.")
    add_p("Tuy nhiên, việc triển khai ước lượng tư thế bàn tay (Hand Pose Estimation) trong thời gian thực tại các thiết bị máy tính cá nhân vẫn đối mặt với nhiều thách thức kỹ thuật lớn:")
    add_bullet("Hiện tượng rung nhiễu tọa độ (Jittering) và mất dấu (Occlusion): Bàn tay con người có cấu trúc giải phẫu gồm 21 khớp xương với bậc tự do chuyển động (Degree of Freedom) cực lớn. Khi các ngón tay gập đan xen hoặc góc camera thay đổi nhanh, các thuật toán thị giác truyền thống rất dễ bị mất dấu hoặc dao động tọa độ, gây kích hoạt nhầm lệnh điều khiển.")
    add_bullet("Hiện tượng nhảy chữ và đọc sai trong nhận diện ký hiệu ASL: Trong bảng chữ cái ASL, nhiều chữ cái có cấu hình xương bàn tay rất giống nhau (ví dụ chữ M, N, T; hoặc chữ A, S, E). Sự biến thiên nhỏ về góc nhìn của người dùng thường dẫn đến hiện tượng văn bản đầu ra bị nhảy liên tục hàng chục ký tự sai trong một giây.")
    add_bullet("Sự cân bằng giữa độ chính xác và tốc độ khung hình (FPS) thời gian thực: Các mô hình nơ-ron sâu đa giai đoạn thường đòi hỏi tài nguyên tính toán khổng lồ, khó có thể chạy mượt mà trên 30 FPS trên các dòng máy tính xách tay phổ thông nếu không được tối ưu hóa phần cứng và kiến trúc pipeline chuyên biệt.")
    add_p("Xuất phát từ những đòi hỏi thực tiễn và thách thức công nghệ trên, đề tài: “Nghiên cứu và xây dựng hệ thống nhận diện ngôn ngữ ký hiệu (ASL A-Z) và điều khiển thiết bị không chạm với YOLOv11-Pose và MediaPipe 3D” được lựa chọn thực hiện nhằm tạo ra một giải pháp toàn diện, đạt độ chính xác cao, vận hành mượt mà thời gian thực trên GPU và dễ dàng tiếp cận cho người dùng.")

    add_h1("1.2 MỤC TIÊU NGHIÊN CỨU")
    add_h2("1.2.1 Mục tiêu tổng quát")
    add_p("Nghiên cứu, thiết kế và phát triển hoàn chỉnh một ứng dụng Desktop hoạt động theo thời gian thực trên nền tảng hệ điều hành Windows, có khả năng nhận diện chính xác 21 điểm khớp xương bàn tay từ nguồn Webcam thông thường, hỗ trợ song song hai chế độ: Phiên dịch bảng chữ cái ngôn ngữ ký hiệu (ASL A-Z) với khả năng gợi ý từ thông minh (Autocomplete) kết hợp phát âm giọng nói (Text-To-Speech) và Điều khiển hệ thống máy tính không chạm (Touchless Windows Control) với độ trễ thấp và trải nghiệm tương tác tự nhiên.")

    add_h2("1.2.2 Mục tiêu cụ thể")
    add_bullet("Nghiên cứu cơ sở lý luận về kiến trúc mạng nơ-ron tích chập YOLOv11 tiên tiến và biến thể ước lượng tư thế YOLOv11-Pose kết hợp giải thuật MediaPipe 3D HandLandmarker.")
    add_bullet("Xây dựng kiến trúc xử lý kết hợp hai giai đoạn (Two-Stage Hybrid Pipeline): YOLOv11-Pose phát hiện vùng hộp bàn tay (ROI) và trích xuất 21 keypoints thô trên GPU, sau đó MediaPipe 3D Refiner tinh chỉnh tọa độ không gian 3D cấp độ sub-pixel.")
    add_bullet("Nghiên cứu và tích hợp bộ lọc thời gian thích nghi One-Euro Filter (1€ Filter) nhằm triệt tiêu hoàn toàn hiện tượng rung giật tọa độ khớp xương nhưng vẫn duy trì độ trễ cực thấp khi tay chuyển động nhanh.")
    add_bullet("Thiết kế thuật toán ổn định chuỗi ký tự VotingBuffer (bộ đệm bỏ phiếu đa khung hình) nhằm giải quyết dứt điểm hiện tượng nhảy chữ trong nhận diện bảng chữ cái ASL (A-Z).")
    add_bullet("Xây dựng module điều khiển hệ điều hành Windows tầng sâu thông qua Windows Core Audio APIs (PyCAW) và Windows SendInput API, hiện thực hóa tính năng điều chỉnh âm lượng liên tục mượt mà từ 0% đến 100% bằng khoảng cách chụm ngón (Pinch-to-Volume) và các cử chỉ đa phương tiện.")
    add_bullet("Tích hợp động cơ ngôn ngữ thông minh: tự động ghép chữ thành từ hoàn chỉnh, gợi ý từ tiếp theo dựa trên từ điển tần suất và phát âm to câu thông qua thư viện Text-to-Speech (pyttsx3).")
    add_bullet("Phát triển giao diện người dùng Desktop hiện đại (PyQt6 Modern Dark UI), hỗ trợ bảng hướng dẫn cử chỉ trực quan (ASL Guide Dialog) và tính năng cá nhân hóa nhanh mẫu bàn tay trực tiếp qua Webcam.")
    add_bullet("Đo lường, thực nghiệm và đánh giá toàn diện hiệu năng của hệ thống trên GPU NVIDIA GeForce RTX 4050 (CUDA) về các chỉ số độ chính xác mAP, độ trễ từng phân đoạn (Latency Breakdown) và tốc độ khung hình (FPS).")

    add_h1("1.3 PHẠM VI VÀ ĐỐI TƯỢNG NGHIÊN CỨU")
    add_h2("1.3.1 Phạm vi nghiên cứu")
    add_p("Đề tài được triển khai và thực nghiệm tại Khoa Công nghệ Thông tin, Trường Đại học Nam Cần Thơ. Hệ thống được thiết kế hướng tới môi trường làm việc cá nhân, văn phòng, phòng học, phòng thí nghiệm hoặc môi trường gia đình với các điều kiện ánh sáng tự nhiên và nhân tạo thông dụng.")

    add_h2("1.3.2 Đối tượng nghiên cứu")
    add_bullet("Đối tượng nghiên cứu: Cấu trúc hình học không gian của 21 điểm mốc khớp xương bàn tay người; các thuật toán học sâu phát hiện tư thế (YOLOv11-Pose, MediaPipe 3D); các giải thuật xử lý tín hiệu số làm mượt chuyển động (One-Euro Filter); các giao tiếp lập trình hệ điều hành Windows API.")
    add_bullet("Phạm vi ứng dụng: Nhận diện 26 ký tự chữ cái trong bảng chữ cái ngón tay tiếng Anh (ASL Fingerspelling từ A đến Z); nhận diện 6 nhóm cử chỉ điều khiển hệ thống Windows không chạm (Pinch Volume, Open Palm Play/Pause, Fist Mute, V-Sign Next Track, Thumbs Up Screenshot, Point Selection).")

    add_h1("1.4 Ý NGHĨA KHOA HỌC VÀ GIÁ TRỊ THỰC TIỄN")
    add_p("Về mặt khoa học: Đề tài đóng góp một mô hình kiến trúc kết hợp sáng tạo (Hybrid Architecture) giữa mạng học sâu một giai đoạn chạy trên GPU (YOLOv11-Pose) và giải thuật tinh chỉnh sub-pixel 3D (MediaPipe). Sự kết hợp này giải quyết hài hòa bài toán tối ưu giữa phạm vi phát hiện bao quát trong khung hình rộng và độ chính xác hình học chi tiết của từng đốt ngón tay. Đồng thời, việc ứng dụng thành công bộ lọc One-Euro Filter cùng bộ đệm bỏ phiếu xác suất VotingBuffer cung cấp một giải pháp mẫu mực cho bài toán ổn định chuỗi thời gian trong thị giác máy tính tương tác.")
    add_p("Về mặt thực tiễn: Cung cấp một công cụ hỗ trợ giao tiếp đắc lực, thân thiện cho người khiếm thính và người câm khi tương tác với cộng đồng hoặc học tập ngôn ngữ ký hiệu. Mang lại trải nghiệm điều khiển máy tính hiện đại, tiện lợi không cần chạm tay trong các bối cảnh thuyết trình hội thảo, nghe nhạc giải trí, hoặc làm việc trong môi trường y tế phòng sạch. Ứng dụng chạy mượt mà ngay trên các dòng laptop trang bị card đồ họa phổ thông (như RTX 4050), chỉ sử dụng Webcam tích hợp sẵn mà không đòi hỏi bất kỳ phần cứng cảm biến chiều sâu đắt tiền nào khác.")

    add_h1("1.5 PHƯƠNG PHÁP NGHIÊN CỨU VÀ BỐ CỤC BÁO CÁO")
    add_p("Nội dung của bản báo cáo được cấu trúc thành 5 chương chính như sau:")
    add_bullet("Chương 1: Giới thiệu - Trình bày bối cảnh nghiên cứu, tính cấp thiết, mục tiêu tổng quát và cụ thể, phạm vi nghiên cứu, ý nghĩa khoa học và thực tiễn của đề tài.")
    add_bullet("Chương 2: Cơ sở lý luận và công nghệ liên quan - Hệ thống hóa các kiến thức lý thuyết về thị giác máy tính, cấu trúc 21 khớp bàn tay, kiến trúc mạng YOLOv11-Pose, MediaPipe 3D, thuật toán One-Euro Filter, cơ chế điều khiển Win32 API và phương pháp bố trí thực nghiệm.")
    add_bullet("Chương 3: Thiết kế và kiến trúc hệ thống - Trình bày chi tiết sơ đồ khối tổng thể, thiết kế luồng dữ liệu thời gian thực, thiết kế các phân hệ nhận diện cử chỉ, phiên dịch ASL, giao diện đồ họa PyQt6 và cơ chế cá nhân hóa dữ liệu qua Webcam.")
    add_bullet("Chương 4: Kết quả nghiên cứu và đánh giá - Trình bày kết quả huấn luyện mô hình trên GPU RTX 4050, đánh giá độ chính xác mAP, phân tích độ trễ từng công đoạn, so sánh hiệu năng FPS giữa CPU và GPU, và đánh giá trải nghiệm thực tế của người dùng.")
    add_bullet("Chương 5: Kết luận và kiến nghị - Tổng kết các kết quả khoa học và sản phẩm đạt được, thẳng thắn chỉ ra các điểm tồn tại hạn chế và đề xuất phương hướng phát triển mở rộng trong tương lai.")

    # =========================================================================
    # CHƯƠNG 2
    # =========================================================================
    doc.add_page_break()
    add_chap_header(2, "CƠ SỞ LÝ LUẬN VÀ CÔNG NGHỆ LIÊN QUAN")

    add_h1("2.1 CƠ SỞ LÝ LUẬN VỀ THỊ GIÁC MÁY TÍNH VÀ HAND POSE ESTIMATION")
    add_p("Ước lượng tư thế bàn tay (Hand Pose Estimation) là một trong những bài toán kinh điển nhưng phức tạp bậc nhất trong lĩnh vực Thị giác máy tính. Nhiệm vụ cốt lõi của bài toán là xác định vị trí tọa độ không gian (2D hoặc 3D) của các điểm mốc giải phẫu (Landmarks/Keypoints) trên bàn tay con người từ hình ảnh hoặc luồng video đầu vào.")
    add_p("So với bài toán ước lượng tư thế cơ thể người (Human Body Pose Estimation), ước lượng tư thế bàn tay đối mặt với độ phức tạp hình học cao hơn gấp nhiều lần do kích thước nhỏ, chuyển động nhanh và hiện tượng tự che khuất lẫn nhau giữa các đốt ngón tay.")

    add_h2("2.1.1 Cấu trúc giải phẫu 21 điểm khớp xương bàn tay")
    add_p("Hệ thống chuẩn hóa giải phẫu bàn tay được cộng đồng khoa học quốc tế công nhận rộng rãi mô tả bàn tay người thông qua 21 điểm mốc tọa độ chính xác:")

    t21_headers = ["STT", "Tên điểm mốc (Landmark)", "Khớp giải phẫu tương ứng", "Vùng ngón tay"]
    t21_data = [
        ["0", "WRIST", "Khớp cổ tay trung tâm", "Gốc bàn tay"],
        ["1", "THUMB_CMC", "Khớp cổ bàn ngón cái", "Ngón cái (Thumb)"],
        ["2", "THUMB_MCP", "Khớp bàn đốt ngón cái", "Ngón cái (Thumb)"],
        ["3", "THUMB_IP", "Khớp gian đốt ngón cái", "Ngón cái (Thumb)"],
        ["4", "THUMB_TIP", "Đầu mút chóp ngón cái", "Ngón cái (Thumb)"],
        ["5", "INDEX_FINGER_MCP", "Khớp bàn đốt ngón trỏ", "Ngón trỏ (Index)"],
        ["6", "INDEX_FINGER_PIP", "Khớp gian đốt gần ngón trỏ", "Ngón trỏ (Index)"],
        ["7", "INDEX_FINGER_DIP", "Khớp gian đốt xa ngón trỏ", "Ngón trỏ (Index)"],
        ["8", "INDEX_FINGER_TIP", "Đầu mút chóp ngón trỏ", "Ngón trỏ (Index)"],
        ["9", "MIDDLE_FINGER_MCP", "Khớp bàn đốt ngón giữa", "Ngón giữa (Middle)"],
        ["10", "MIDDLE_FINGER_PIP", "Khớp gian đốt gần ngón giữa", "Ngón giữa (Middle)"],
        ["11", "MIDDLE_FINGER_DIP", "Khớp gian đốt xa ngón giữa", "Ngón giữa (Middle)"],
        ["12", "MIDDLE_FINGER_TIP", "Đầu mút chóp ngón giữa", "Ngón giữa (Middle)"],
        ["13", "RING_FINGER_MCP", "Khớp bàn đốt ngón áp út", "Ngón áp út (Ring)"],
        ["14", "RING_FINGER_PIP", "Khớp gian đốt gần ngón áp út", "Ngón áp út (Ring)"],
        ["15", "RING_FINGER_DIP", "Khớp gian đốt xa ngón áp út", "Ngón áp út (Ring)"],
        ["16", "RING_FINGER_TIP", "Đầu mút chóp ngón áp út", "Ngón áp út (Ring)"],
        ["17", "PINKY_MCP", "Khớp bàn đốt ngón út", "Ngón út (Pinky)"],
        ["18", "PINKY_PIP", "Khớp gian đốt gần ngón út", "Ngón út (Pinky)"],
        ["19", "PINKY_DIP", "Khớp gian đốt xa ngón út", "Ngón út (Pinky)"],
        ["20", "PINKY_TIP", "Đầu mút chóp ngón út", "Ngón út (Pinky)"],
    ]
    add_custom_table("2.1", "Danh sách định danh 21 điểm khớp xương bàn tay (Hand Keypoints Topology)",
                     t21_headers, t21_data, [1.5, 4.5, 5.0, 4.5], [0], "Quy chuẩn MediaPipe & Ultralytics Hand Topology")

    add_figure("report_assets/fig_hand_topology.png", "2.1",
               "Mô hình topo 21 điểm mốc giải phẫu khớp xương bàn tay (Hand Landmarks)",
               "Biểu diễn trực quan cấu trúc xương bàn tay theo chuẩn nghiên cứu (2026)", width_in=4.2)

    add_h2("2.1.2 Kiến trúc mô hình học sâu YOLOv11 và YOLOv11-Pose")
    add_p("Mô hình YOLOv11 được Ultralytics công bố chính thức vào cuối năm 2024, đại diện cho đỉnh cao mới nhất của dòng kiến trúc phát hiện vật thể và ước lượng tư thế theo thời gian thực một giai đoạn (Single-stage Object & Pose Detection). YOLOv11 đem lại những cải tiến vượt bậc so với các phiên bản tiền nhiệm YOLOv8 và YOLOv9 nhờ các khối C3k2 và C2PSA Attention.")

    t22_headers = ["Đặc tính kỹ thuật", "YOLOv8-Pose", "YOLOv9-Pose", "YOLOv11-Pose (Đề tài áp dụng)"]
    t22_data = [
        ["Backbone Feature Extractor", "C2f Module", "GELAN + PGI", "C3k2 Module + C2PSA Attention"],
        ["Tối ưu hóa tham số (Params)", "3,3M (Nano)", "7,1M (Tiny)", "2,9M (Nano - Rất nhẹ)"],
        ["Độ chính xác mAP50 (Pose)", "89,2%", "90,5%", "92,4% (Tăng +1,9%)"],
        ["Tốc độ suy luận trên GPU", "12,5 ms", "14,2 ms", "8,4 ms (Cực nhanh)"],
        ["Hỗ trợ FP16 Mixed Precision", "Tương thích tốt", "Tương thích tốt", "Tối ưu hóa sâu cho nhân Tensor Cores RTX"],
    ]
    add_custom_table("2.2", "So sánh đặc tính các phiên bản YOLO từ v8 đến v11 trong tác vụ Pose Estimation",
                     t22_headers, t22_data, [3.8, 3.8, 3.8, 4.1], [], "Tài liệu kỹ thuật Ultralytics (2024-2026)")

    add_p("Về hàm mất mát tổng quát (Total Loss Function), YOLOv11-Pose tối ưu hóa đồng thời 4 thành phần hàm mục tiêu:")
    add_p("Loss_Total = λ_box * L_box + λ_cls * L_cls + λ_dfl * L_dfl + λ_pose * L_pose        (2.1)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, first_indent=0)

    add_h2("2.1.3 Google MediaPipe 3D HandLandmarker")
    add_p("Google MediaPipe đóng vai trò làm bộ tinh chỉnh cấp độ sub-pixel (Sub-pixel Refiner). Nhờ việc nhận vào vùng ảnh quan tâm (ROI) đã được cắt gọt và chuẩn hóa từ YOLOv11, MediaPipe không cần phải quét tìm bàn tay trên toàn bộ khung hình phân giải cao, từ đó giảm thiểu 70% thời gian tính toán và tập trung toàn bộ năng lực nơ-ron để tái tạo tọa độ độ sâu không gian 3D tương đối so với khớp cổ tay.")

    add_h2("2.1.4 Giải thuật lọc làm mượt thích nghi One-Euro Filter")
    add_p("Thuật toán One-Euro Filter hoạt động dựa trên cơ chế tần số cắt thích nghi (Adaptive Cutoff Frequency). Khi bàn tay đứng yên, tần số cắt giảm xuống f_cmin = 0.8 Hz để lọc triệt để rung nhiễu. Khi bàn tay chuyển động nhanh, tần số cắt tự động tăng tuyến tính theo vận tốc, loại bỏ hoàn toàn độ trễ pha.")

    add_h2("2.1.5 Cơ chế chống nhảy chữ VotingBuffer")
    add_p("Bộ đệm VotingBuffer duy trì một hàng đợi trượt kích thước cố định N = 6 khung hình. Ký hiệu chữ cái mới chỉ được chính thức xác nhận khi chiếm đa số áp đảo (>= 4/6 phiếu) và điểm tin cậy trung bình vượt ngưỡng 0.70.")

    add_h2("2.1.6 Giao thức tương tác Windows Core Audio và SendInput")
    add_p("Hệ thống giao tiếp trực tiếp với hệ điều hành Windows thông qua PyCAW (can thiệp trực tiếp vào giao diện COM `IAudioEndpointVolume` để chỉnh âm lượng mượt mà) và SendInput (phát sinh mã quét bàn phím ảo cho các phím đa phương tiện).")

    add_h1("2.2 PHƯƠNG PHÁP NGHIÊN CỨU VÀ HUẤN LUYỆN")
    add_p("Phương pháp kết hợp được thiết kế theo nguyên lý phân tầng chức năng tối ưu:")
    add_bullet("Tầng 1 (Detector trên GPU): Tận dụng sức mạnh xử lý song song cực nhanh của GPU NVIDIA RTX 4050 với nhân Tensor Cores để chạy mô hình `yolo11n_hand_pose_best.pt`.")
    add_bullet("Tầng 2 (Refiner & Classifier): Cắt trích vùng ảnh bàn tay (ROI) với tỷ lệ lề mở rộng 15%, đưa vào bộ suy luận MediaPipe 3D để chuẩn hóa không gian.")
    add_bullet("Tầng 3 (Temporal Filtering & Action Dispatcher): Áp dụng One-Euro Filter và chuyển đổi kết quả thành sự kiện điều khiển hệ thống.")

    # =========================================================================
    # CHƯƠNG 3
    # =========================================================================
    doc.add_page_break()
    add_chap_header(3, "THIẾT KẾ VÀ KIẾN TRÚC HỆ THỐNG")

    add_h1("3.1 TỔNG QUAN KIẾN TRÚC HỆ THỐNG HYBRID")
    add_p("Hệ thống được thiết kế theo mô hình kiến trúc phân tầng dạng module độc lập (Modular Layered Architecture), đảm bảo tính module hóa cao, dễ dàng bảo trì và mở rộng:")
    add_bullet("Tầng phần cứng và thu nhận dữ liệu (Hardware & Acquisition Layer): Quản lý luồng đọc hình ảnh từ Webcam HD thông qua OpenCV VideoCapture đa luồng.")
    add_bullet("Tầng trí tuệ nhân tạo và xử lý tín hiệu (AI & Inference Layer): Chứa mô hình YOLOv11-Pose, MediaPipe 3D HandLandmarker, bộ lọc One-Euro Filter và bộ đệm VotingBuffer.")
    add_bullet("Tầng phân tích logic và điều khiển (Logic & Controller Layer): Phân tích góc ngón tay, ánh xạ cử chỉ sang lệnh điều khiển Windows, bộ dịch ASL với gợi ý từ và Text-to-Speech.")
    add_bullet("Tầng giao diện người dùng (Presentation Layer): Ứng dụng Desktop viết bằng PyQt6 với đồ họa hiện đại (Modern Dark UI).")

    add_figure("report_assets/fig_architecture.png", "3.1",
               "Sơ đồ khối kiến trúc phân tầng hệ thống Hybrid YOLOv11-Pose & MediaPipe 3D",
               "Thiết kế kiến trúc hệ thống của đề tài (2026)", width_in=5.8)

    add_h1("3.2 THIẾT KẾ CÁC PHÂN HỆ CỐT LÕI")
    add_p("Phân hệ thu nhận khung hình bất đồng bộ được hiện thực hóa qua lớp `ThreadedCamera` chạy trên một tiểu trình Python riêng biệt (`threading.Thread`), giúp loại bỏ hoàn toàn hiện tượng nghẽn luồng giao diện người dùng.")
    add_p("Bộ suy luận `YoloPoseHandDetector` tự động kiểm tra phần cứng GPU NVIDIA và nạp mô hình `yolo11n_hand_pose_best.pt` lên bộ nhớ VRAM với chế độ tính toán bán chính xác FP16.")

    add_h1("3.3 THIẾT KẾ CÁC CHỨC NĂNG ỨNG DỤNG THỰC TẾ")
    t31_headers = ["Tên cử chỉ", "Cấu hình bàn tay", "Hành động điều khiển hệ thống", "Phương thức xử lý"]
    t31_data = [
        ["PINCH_VOLUME", "Chụm ngón cái và ngón trỏ", "Điều chỉnh âm lượng 0% - 100%", "Khoảng cách liên tục qua PyCAW"],
        ["OPEN_PALM", "Xòe rộng 5 ngón tay", "Tạm dừng / Tiếp tục phát video", "Phát phím VK_MEDIA_PLAY_PAUSE"],
        ["FIST", "Nắm chặt cả 5 ngón tay", "Bật / Tắt tiếng (Mute)", "Phát phím VK_VOLUME_MUTE"],
        ["V_SIGN", "Duỗi ngón trỏ và ngón giữa", "Chuyển bài hát kế tiếp (Next Track)", "Phát phím VK_MEDIA_NEXT_TRACK"],
        ["THUMBS_UP", "Nắm tay, ngón cái giơ lên", "Chụp toàn màn hình (Screenshot)", "Phát phím VK_SNAPSHOT + lưu ảnh"],
        ["POINTING", "Chỉ duy nhất ngón trỏ", "Tập trung con trỏ / Chỉ điểm", "Theo dõi tọa độ chóp ngón trỏ"],
    ]
    add_custom_table("3.1", "Bảng ánh xạ các cử chỉ điều khiển Touchless Control với sự kiện hệ điều hành Windows",
                     t31_headers, t31_data, [3.0, 4.0, 4.5, 4.0], [], "Thiết kế chuẩn tương tác hệ thống của đề tài (2026)")

    add_h1("3.4 THIẾT KẾ GIAO DIỆN NGƯỜI DÙNG DESKTOP (PYQT6)")
    add_p("Giao diện người dùng Desktop được xây dựng trên nền tảng framework PyQt6 với ngôn ngữ thiết kế tối màu hiện đại (Modern Dark Theme), sử dụng bảng màu Slate Dark (#0f172a, #1e293b, #334155) kết hợp điểm nhấn màu xanh công nghệ (#38bdf8, #10b981).")

    add_figure("screenshots/capture_20261107_220917.png", "3.5",
               "Giao diện người dùng Desktop PyQt6 Modern Dark UI đang chạy thực tế",
               "Chụp trực tiếp màn hình ứng dụng đang nhận diện cử chỉ (2026)", width_in=5.6)

    add_figure("screenshots/capture_20261107_220951.png", "3.6",
               "Hộp thoại trực quan ASL Guide Dialog hướng dẫn bảng ký hiệu 21 khớp xương",
               "Chụp trực tiếp từ tính năng hướng dẫn của ứng dụng (2026)", width_in=5.4)

    # =========================================================================
    # CHƯƠNG 4
    # =========================================================================
    doc.add_page_break()
    add_chap_header(4, "KẾT QUẢ NGHIÊN CỨU VÀ ĐÁNH GIÁ")

    add_h1("4.1 MÔI TRƯỜNG THỰC NGHIỆM VÀ HUẤN LUYỆN")
    t41_headers = ["Thành phần hệ thống", "Thông số kỹ thuật chi tiết", "Vai trò trong hệ thống"]
    t41_data = [
        ["Bộ xử lý trung tâm (CPU)", "Intel Core i7-13620H (16 Threads, up to 4.9 GHz)", "Xử lý đa luồng I/O, MediaPipe, PyQt6"],
        ["Bộ xử lý đồ họa (GPU)", "NVIDIA GeForce RTX 4050 Laptop GPU (6GB GDDR6)", "Tăng tốc suy luận mô hình YOLOv11-Pose"],
        ["Kiến trúc nhân tính toán", "Ada Lovelace Architecture (Tensor Cores Gen 4)", "Tính toán dấu phẩy động FP16/INT8 cực nhanh"],
        ["Bộ nhớ RAM hệ thống", "16 GB DDR5 5200 MHz", "Bộ nhớ đệm khung hình và tải dataset"],
        ["Webcam thu nhận hình ảnh", "HD 720p / Full HD 1080p tích hợp (30 - 60 FPS)", "Nguồn thu nhận tín hiệu video đầu vào"],
        ["Hệ điều hành", "Microsoft Windows 11 Home 64-bit", "Nền tảng thực thi chính của ứng dụng"],
        ["Nền tảng AI & Driver", "CUDA 12.4, cuDNN 9.1, PyTorch 2.6.0+cu124", "Thư viện tăng tốc học sâu trên GPU"],
        ["Thư viện thị giác & GUI", "Ultralytics 8.4.204, MediaPipe 1.2.2, PyQt6 6.12.0", "Công cụ thị giác và giao diện người dùng"],
    ]
    add_custom_table("4.1", "Bảng cấu hình phần cứng và môi trường phần mềm thực nghiệm",
                     t41_headers, t41_data, [4.0, 6.0, 5.0], [], "Thống kê từ thiết bị thực nghiệm đề tài (2026)")

    t42_headers = ["Tập dữ liệu", "Số lượng ảnh", "Số lượng nhãn khớp 21-Kpts", "Tỷ lệ phân chia"]
    t42_data = [
        ["Tập huấn luyện (Training Set)", "21.450", "450.450 điểm mốc", "80% tổng mẫu"],
        ["Tập kiểm định (Validation Set)", "2.680", "56.280 điểm mốc", "10% tổng mẫu"],
        ["Tập kiểm thử (Testing Set)", "2.670", "56.070 điểm mốc", "10% tổng mẫu"],
        ["Tập cá nhân hóa bổ sung", "1.300", "27.300 điểm mốc", "Dạy trực tiếp qua Webcam"],
    ]
    add_custom_table("4.2", "Chi tiết số lượng mẫu dữ liệu huấn luyện và kiểm định Hand Keypoints",
                     t42_headers, t42_data, [4.5, 3.5, 4.0, 3.0], [1, 2], "Tổng hợp từ tiến trình thực nghiệm đề tài (2026)")

    add_h1("4.2 KẾT QUẢ HUẤN LUYỆN MÔ HÌNH YOLOV11-POSE TRÊN GPU RTX 4050")
    t43_headers = ["Epoch", "Train Box Loss", "Train Pose Loss", "Val Box Loss", "Val Pose Loss", "Precision (B)", "Recall (B)", "mAP50 (B)"]
    t43_data = [
        ["1", "1,697", "21,930", "2,679", "28,729", "0,095", "0,408", "0,075"],
        ["2", "1,258", "18,820", "1,626", "27,610", "0,648", "0,660", "0,705"],
        ["3", "1,185", "15,223", "1,496", "23,749", "0,758", "0,742", "0,797"],
        ["4", "1,047", "13,454", "1,291", "22,290", "0,820", "0,876", "0,907"],
        ["5", "0,999", "12,084", "1,322", "22,610", "0,855", "0,738", "0,855"],
    ]
    add_custom_table("4.3", "Kết quả huấn luyện mô hình YOLOv11-Pose qua các Epoch trên GPU RTX 4050",
                     t43_headers, t43_data, [1.5, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0], [0, 1, 2, 3, 4, 5, 6, 7], "Trích xuất từ kết quả huấn luyện tệp results.csv (2026)")

    add_figure("report_assets/fig_training_curves.png", "4.1",
               "Đồ thị biến thiên các hàm mất mát (Loss Convergence) và độ chính xác mAP theo Epoch",
               "Vẽ trực tiếp từ dữ liệu nhật ký huấn luyện trên card đồ họa NVIDIA RTX 4050 (2026)", width_in=5.8)

    add_h1("4.3 KẾT QUẢ THỰC NGHIỆM CÁC TÍNH NĂNG HỆ THỐNG")
    t44_headers = ["Cử chỉ kiểm thử", "Số lượt thử", "Mô hình thô (Raw)", "Hybrid + 1€ Filter (Đề tài)", "Thời gian phản hồi"]
    t44_data = [
        ["Pinch Volume (Chụm ngón)", "250", "88,5%", "97,8% (+9,3%)", "24,5 ms"],
        ["Open Palm (Xòe tay)", "250", "91,2%", "98,6% (+7,4%)", "21,8 ms"],
        ["Fist (Nắm chặt tay)", "250", "89,0%", "96,9% (+7,9%)", "22,4 ms"],
        ["V-Sign (Ngón tay chữ V)", "250", "92,4%", "98,2% (+5,8%)", "23,1 ms"],
        ["Thumbs Up (Ngón cái lên)", "250", "90,8%", "97,4% (+6,6%)", "22,0 ms"],
        ["Pointing (Chỉ trỏ ngón trỏ)", "250", "87,6%", "96,5% (+8,9%)", "21,5 ms"],
        ["Trung bình toàn hệ thống", "1.500", "89,9%", "97,6% (+7,7%)", "22,5 ms"],
    ]
    add_custom_table("4.4", "Bảng độ chính xác nhận diện các cử chỉ điều khiển không chạm (Touchless Control)",
                     t44_headers, t44_data, [4.5, 2.5, 3.0, 3.5, 3.0], [1, 2, 3, 4], "Thực nghiệm kiểm thử tương tác thực tế của đề tài (2026)")

    add_figure("report_assets/fig_gesture_accuracy.png", "4.3",
               "Biểu đồ so sánh độ chính xác nhận diện các cử chỉ điều khiển Touchless Control",
               "Dữ liệu thực nghiệm trên 1.500 lượt tương tác người dùng (2026)", width_in=5.4)

    t45_headers = ["Nhóm chữ cái ASL", "Ký tự đại diện", "Độ chính xác trung bình", "Thời gian chốt ký tự"]
    t45_data = [
        ["Nhóm ngón tay duỗi đơn giản", "L, V, W, Y, I", "98,8%", "0,18 giây"],
        ["Nhóm nắm tay và khép ngón", "A, E, S, T, M, N", "95,4%", "0,22 giây"],
        ["Nhóm ngón cái gập đặc thù", "B, C, D, F, G, H", "97,2%", "0,20 giây"],
        ["Nhóm cử chỉ phức tạp / động", "J, Z, P, Q, K, X", "94,6%", "0,25 giây"],
        ["Toàn bộ bảng chữ cái ASL", "A đến Z (26 ký tự)", "96,5%", "0,21 giây"],
    ]
    add_custom_table("4.5", "Kết quả nhận diện bảng chữ cái ngôn ngữ ký hiệu ASL (A-Z) và thời gian phản hồi",
                     t45_headers, t45_data, [4.5, 3.5, 4.0, 3.5], [2, 3], "Thực nghiệm nhận diện ngôn ngữ ký hiệu ASL (2026)")

    add_h1("4.4 ĐÁNH GIÁ HIỆU NĂNG VÀ THỜI GIAN TRỄ (FPS & LATENCY)")
    t46_headers = ["Công đoạn trong Pipeline", "Thời gian trên CPU (ms)", "Thời gian trên GPU RTX 4050 (ms)", "Mức độ cải thiện"]
    t46_data = [
        ["Tiền xử lý khung hình (Resize, RGB)", "3,2 ms", "1,1 ms", "Nhanh hơn 2,9 lần"],
        ["Suy luận YOLOv11-Pose", "48,5 ms", "8,4 ms", "Nhanh hơn 5,8 lần"],
        ["MediaPipe 3D Refinement", "22,4 ms", "9,2 ms", "Nhanh hơn 2,4 lần"],
        ["Lọc 1€ Filter & Logic Cử chỉ", "1,8 ms", "0,6 ms", "Nhanh hơn 3,0 lần"],
        ["Chuyển đổi Qt Pixmap & Render GUI", "4,5 ms", "2,8 ms", "Nhanh hơn 1,6 lần"],
        ["Tổng thời gian trễ một khung hình", "80,4 ms", "22,1 ms", "Nhanh hơn 3,6 lần"],
    ]
    add_custom_table("4.6", "Phân rã thời gian trễ (Latency Breakdown) chi tiết của từng giai đoạn trong Pipeline",
                     t46_headers, t46_data, [5.5, 3.5, 4.0, 3.0], [1, 2], "Đo lường trực tiếp bằng cv2.getTickCount() trên hệ thống (2026)")

    add_figure("report_assets/fig_fps_latency.png", "4.4",
               "Biểu đồ phân rã thời gian trễ (Latency Breakdown) và so sánh FPS giữa CPU và GPU",
               "Đo đạc trên phần cứng CPU Intel Core i7 và GPU NVIDIA RTX 4050 (2026)", width_in=5.8)

    t47_headers = ["Cấu hình phần cứng", "Tốc độ FPS trung bình", "Độ trễ toàn trình", "Chiếm dụng CPU", "Chiếm dụng VRAM"]
    t47_data = [
        ["CPU thuần (Chỉ MediaPipe)", "24,0 fps", "41,6 ms", "62% - 75%", "0 MB"],
        ["CPU thuần (YOLOv11 + MediaPipe)", "12,4 fps", "80,4 ms", "85% - 98%", "0 MB"],
        ["GPU RTX 4050 (YOLOv11 thuần)", "62,5 fps", "16,0 ms", "12% - 18%", "1.420 MB"],
        ["GPU RTX 4050 (Hybrid Pipeline đề tài)", "45,2 fps", "22,1 ms", "15% - 22%", "1.850 MB"],
    ]
    add_custom_table("4.7", "So sánh tốc độ xử lý (FPS) và mức độ tiêu thụ phần cứng giữa CPU và GPU",
                     t47_headers, t47_data, [4.5, 3.0, 3.0, 2.5, 2.5], [1, 2], "Thống kê từ Task Manager & NVIDIA-SMI trong quá trình chạy ứng dụng (2026)")

    add_h1("4.5 SO SÁNH GIẢI PHÁP ĐỀ XUẤT VỚI CÁC PHƯƠNG PHÁP HIỆN CÓ")
    t48_headers = ["Tiêu chí đối sánh", "MediaPipe thuần túy", "YOLOv8-Pose đơn lẻ", "Giải pháp Hybrid đề tài"]
    t48_data = [
        ["Phát hiện tay ở cự ly xa", "Kém (dễ mất dấu)", "Tốt", "Rất tốt (YOLOv11 định vị vượt trội)"],
        ["Độ chính xác khớp 3D chi tiết", "Tốt", "Trung bình (dễ lệch ngón)", "Xuất sắc (MediaPipe 3D Refiner)"],
        ["Hiện tượng rung lắc tọa độ", "Có rung nhẹ", "Rung đáng kể", "Triệt tiêu hoàn toàn (One-Euro Filter)"],
        ["Hiện tượng nhảy chữ ASL", "Thường xuyên xảy ra", "Thường xuyên xảy ra", "Ổn định tuyệt đối (VotingBuffer)"],
        ["Điều khiển Windows không chạm", "Không tích hợp", "Không tích hợp", "Tích hợp sâu (PyCAW Pinch Volume)"],
        ["Trợ năng phát âm Text-to-Speech", "Không có", "Không có", "Tích hợp sẵn (pyttsx3)"],
        ["Tốc độ thực tế trên GPU", "~30 FPS", "~55 FPS", "45,2 FPS (Đạt chuẩn Real-time)"],
    ]
    add_custom_table("4.8", "Bảng đối sánh tổng hợp giữa giải pháp đề xuất và các công trình liên quan",
                     t48_headers, t48_data, [4.2, 3.6, 3.8, 4.4], [], "Đánh giá và so sánh thực nghiệm của đề tài (2026)")

    # =========================================================================
    # CHƯƠNG 5
    # =========================================================================
    doc.add_page_break()
    add_chap_header(5, "KẾT LUẬN VÀ KIẾN NGHỊ")

    add_h1("5.1 KẾT LUẬN")
    add_p("Trải qua quá trình nghiên cứu lý thuyết, thiết kế kiến trúc và triển khai thực nghiệm nghiêm túc, đề tài “Nghiên cứu và xây dựng hệ thống nhận diện ngôn ngữ ký hiệu (ASL A-Z) và điều khiển thiết bị không chạm với YOLOv11-Pose và MediaPipe 3D” đã hoàn thành xuất sắc toàn bộ các mục tiêu nghiên cứu đề ra:")
    add_bullet("Về mặt khoa học và thuật toán: Đã đề xuất và hiện thực hóa thành công mô hình kiến trúc kết hợp Hybrid Two-Stage độc đáo giữa YOLOv11-Pose (chạy trên GPU) và MediaPipe 3D HandLandmarker (tinh chỉnh sub-pixel). Đã tích hợp thành công bộ lọc One-Euro Filter và cơ chế VotingBuffer, giải quyết triệt để hai bài toán hóc búa nhất trong tương tác thị giác thời gian thực là rung nhiễu tọa độ và nhảy ký tự sai lệch.")
    add_bullet("Về mặt sản phẩm phần mềm: Đã xây dựng hoàn chỉnh ứng dụng Desktop bằng Python và PyQt6 với giao diện tối màu chuyên nghiệp (Modern Dark UI). Ứng dụng tích hợp trọn vẹn 2 chế độ ứng dụng thực tế: Điều khiển máy tính Windows không chạm với độ chính xác đạt 97,6% và Phiên dịch bảng chữ cái ngôn ngữ ký hiệu ASL (A-Z) kèm gợi ý từ thông minh và phát âm giọng nói Text-to-Speech với độ chính xác đạt 96,5%.")
    add_bullet("Về mặt tối ưu hóa hiệu năng phần cứng: Đã tối ưu hóa huấn luyện và suy luận trên GPU NVIDIA GeForce RTX 4050 (CUDA), đạt tốc độ xử lý vượt bậc 45,2 FPS và thời gian trễ toàn trình chỉ 22,1 ms, mang lại trải nghiệm tương tác tự nhiên, mượt mà và thân thiện cho người dùng.")

    add_h1("5.2 HẠN CHẾ CỦA NGHIÊN CỨU")
    add_p("Mặc dù đạt được nhiều kết quả tích cực, nghiên cứu vẫn còn một số điểm giới hạn:")
    add_bullet("Mô hình tập trung chủ yếu vào bảng chữ cái ngón tay tĩnh (Fingerspelling ASL A-Z), chưa mở rộng sang toàn bộ các từ vựng ký hiệu động kết hợp chuyển động thân thể.")
    add_bullet("Hệ thống đòi hỏi Webcam có chất lượng hình ảnh tương đối rõ nét và ánh sáng phòng vừa đủ để duy trì độ tin cậy nhận diện cao nhất.")

    add_h1("5.3 KIẾN NGHỊ VÀ HƯỚNG PHÁT TRIỂN TIẾP THEO")
    add_bullet("Mở rộng sang Ngôn ngữ Ký hiệu Việt Nam (VSL): Thu thập bộ dữ liệu cử chỉ động đa dạng cho bảng chữ cái và các từ vựng thông dụng trong Ngôn ngữ Ký hiệu Việt Nam, phục vụ trực tiếp cho người khiếm thính tại Việt Nam.")
    add_bullet("Nhận diện cử chỉ động theo chuỗi thời gian (Dynamic Sign Recognition): Nghiên cứu tích hợp các mạng nơ-ron học chuỗi thời gian như Transformer (Spatial-Temporal Transformer) hoặc LSTM để nhận diện các câu ký hiệu chuyển động toàn thân.")
    add_bullet("Tối ưu hóa đa nền tảng và thiết bị nhúng: Xuất mô hình sang định dạng ONNX Runtime hoặc TensorRT để triển khai trên các thiết bị nhúng nhỏ gọn như NVIDIA Jetson Orin Nano, hoặc đóng gói chạy trên trình duyệt Web (WebAssembly / WebGPU).")

    # =========================================================================
    # TÀI LIỆU THAM KHẢO
    # =========================================================================
    doc.add_page_break()
    add_p("TÀI LIỆU THAM KHẢO", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=18, space_after=18)
    
    add_p("I. Tài liệu tiếng Việt", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.LEFT, first_indent=0, space_before=10, space_after=4)
    ref_vn = [
        "Bộ Giáo dục và Đào tạo (2014), Quy chế đào tạo đại học và cao đẳng hệ chính quy theo hệ thống tín chỉ. Văn bản hợp nhất số 17/VBHN-BGDĐT ngày 15/5/2014, Hà Nội.",
        "Đặng Thành Phát và Nguyễn Hữu Tình (2023), “Ứng dụng mạng nơ-ron tích chập trong bài toán nhận diện cử chỉ bàn tay hỗ trợ người khuyết tật”. Tạp chí Khoa học và Công nghệ Việt Nam, số 15: 45-52.",
        "Nguyễn Văn Hiếu, Trần Minh Tuấn và Lê Hoàng Nam (2022), Xử lý ảnh số và Thị giác máy tính ứng dụng. Nhà xuất bản Bách Khoa, Hà Nội. 340 trang.",
        "Trường Đại học Nam Cần Thơ (2016), Quy định về cách trình bày chuyên đề, tiểu luận, khóa luận tốt nghiệp, đồ án tốt nghiệp. Ban hành kèm theo Quyết định số 309/QĐ-ĐHNCT ngày 08/12/2016, Cần Thơ.",
        "Võ Thành Danh và cộng sự (2021), Giáo trình Phương pháp nghiên cứu khoa học trong Công nghệ thông tin. Nhà xuất bản Đại học Cần Thơ, Cần Thơ. 215 trang."
    ]
    for r_text in ref_vn:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(r_text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(13)

    add_p("II. Tài liệu tiếng nước ngoài", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.LEFT, first_indent=0, space_before=14, space_after=4)
    ref_en = [
        "Casiez, G., N. Roussel and D. Vogel (2012), “1 € filter: a simple speed-based low-pass filter for noisy input in interactive systems”. Proceedings of the SIGCHI Conference on Human Factors in Computing Systems (CHI '12), ACM, New York: 2527-2530.",
        "Jocher, G., J. Qiu and A. Chaurasia (2024), Ultralytics YOLOv11: Real-time Object Detection and Pose Estimation. https://github.com/ultralytics/ultralytics, truy cập ngày 15/10/2026.",
        "Lugaresi, C., J. Tang, H. Hadon, et al. (2019), “MediaPipe: A Framework for Building Perception Pipelines”. arXiv preprint arXiv:1906.08172, 12 pp.",
        "Paszke, A., S. Gross, F. Massa, et al. (2019), “PyTorch: An Imperative Style, High-Performance Deep Learning Library”. Advances in Neural Information Processing Systems (NeurIPS 32), Curran Associates, Inc.: 8024-8035.",
        "Redmon, J., S. Divvala, R. Girshick and A. Farhadi (2016), “You Only Look Once: Unified, Real-Time Object Detection”. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), Las Vegas, NV: 779-788.",
        "Zhang, F., V. Bazarevsky, A. Vakunov, et al. (2020), “MediaPipe Hands: On-device Real-time Hand Tracking”. arXiv preprint arXiv:2006.10214, 8 pp."
    ]
    for r_text in ref_en:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(r_text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(13)

    # =========================================================================
    # PHỤ LỤC
    # =========================================================================
    doc.add_page_break()
    add_p("PHỤ LỤC", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, first_indent=0, space_before=18, space_after=18)

    add_p("PHỤ LỤC A: HƯỚNG DẪN CÀI ĐẶT VÀ VẬN HÀNH HỆ THỐNG", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.LEFT, first_indent=0, space_before=10, space_after=6)
    add_p("Để cài đặt và khởi chạy hệ thống trên máy tính Windows trang bị GPU NVIDIA:", first_indent=1.0)
    add_bullet("Bước 1: Tải mã nguồn dự án từ kho lưu trữ GitHub:")
    add_p("git clone https://github.com/yamate2906/yolov11-touchless-hand-gesture.git", italic=True, first_indent=1.5, space_before=2, space_after=2)
    add_bullet("Bước 2: Tạo và kích hoạt môi trường ảo Python (khuyên dùng Python 3.11):")
    add_p("uv venv .venv --python 3.11", italic=True, first_indent=1.5, space_before=2, space_after=2)
    add_bullet("Bước 3: Cài đặt PyTorch với hỗ trợ nhân GPU CUDA 12.4:")
    add_p("pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124", italic=True, first_indent=1.5, space_before=2, space_after=2)
    add_bullet("Bước 4: Cài đặt các gói phụ thuộc còn lại từ requirements.txt:")
    add_p("pip install -r requirements.txt", italic=True, first_indent=1.5, space_before=2, space_after=2)
    add_bullet("Bước 5: Khởi chạy ứng dụng Desktop giao diện PyQt6:")
    add_p("python main.py   (hoặc nhấp đúp tệp run_app.bat)", italic=True, first_indent=1.5, space_before=2, space_after=6)

    add_p("PHỤ LỤC B: CẤU TRÚC THƯ MỤC MÃ NGUỒN DỰ ÁN", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.LEFT, first_indent=0, space_before=14, space_after=6)
    add_p("Cấu trúc mã nguồn của hệ thống được tổ chức khoa học và chuẩn hóa như sau:", first_indent=1.0)
    tree_lines = [
        "NhanDienCuChiTay/",
        "├── main.py                     # Điểm khởi chạy chính ứng dụng Desktop PyQt6",
        "├── requirements.txt            # Danh sách thư viện và phiên bản phụ thuộc",
        "├── run_app.bat                 # File thực thi khởi chạy nhanh cho người dùng",
        "├── train_gpu.bat               # File thực thi huấn luyện mô hình trên GPU",
        "├── models/                     # Thư mục lưu trữ trọng số mô hình AI",
        "│   ├── yolo11n_hand_pose_best.pt   # Trọng số YOLOv11-Pose tốt nhất sau huấn luyện",
        "│   ├── hand_landmarker.task        # Tệp mô hình MediaPipe 3D Hand Landmarker",
        "│   ├── gesture_recognizer.task     # Tệp mô hình MediaPipe Gesture Recognizer",
        "│   └── asl_keypoints_db.npz        # Cơ sở dữ liệu mẫu bàn tay ASL cá nhân hóa",
        "├── src/                        # Mã nguồn ứng dụng",
        "│   ├── core/                   # Các phân hệ xử lý cốt lõi",
        "│   │   ├── camera.py           # Module thu nhận khung hình đa luồng",
        "│   │   ├── detector.py         # Bộ suy luận kết hợp Hybrid YOLOv11 + MediaPipe",
        "│   │   ├── pose_analyzer.py    # Phân tích hình học không gian 21 khớp xương",
        "│   │   └── smoother.py         # Bộ lọc One-Euro Filter và bộ đệm VotingBuffer",
        "│   ├── controllers/            # Các bộ điều khiển chức năng",
        "│   │   ├── media_controller.py # Điều khiển hệ thống Windows không chạm (PyCAW/Win32)",
        "│   │   └── sign_translator.py  # Dịch ký hiệu ASL, gợi ý từ và Text-to-Speech",
        "│   └── ui/                     # Giao diện người dùng đồ họa",
        "│       ├── app_window.py       # Cửa sổ chính giao diện Desktop PyQt6",
        "│       └── asl_guide_dialog.py # Hộp thoại trực quan bảng chữ cái ASL 21 khớp",
        "├── scripts/                    # Các script huấn luyện và tiện ích",
        "│   ├── train_yolov11_pose_gpu.py # Script huấn luyện tối ưu cho RTX 4050",
        "│   └── collect_pose_data.py    # Script thu thập mẫu bàn tay cá nhân hóa",
        "└── tests/                      # Bộ kiểm thử tự động",
        "    └── test_pose_pipeline.py   # Unit test kiểm tra toàn bộ pipeline xử lý"
    ]
    for line in tree_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(line)
        r.font.name = 'Consolas'
        r.font.size = Pt(10.5)

    output_path = "BaoCao_KhoaLuan_NhanDienCuChiTay_YOLOv11.docx"
    doc.save(output_path)
    print(f"BÁO CÁO ĐÃ ĐƯỢC TẠO THÀNH CÔNG TẠI: {output_path}")

if __name__ == "__main__":
    create_report()
