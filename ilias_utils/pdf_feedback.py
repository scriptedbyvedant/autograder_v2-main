
# ilias_utils/pdf_feedback.py
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors
from PIL import Image as PILImage

class FeedbackPDFGenerator:
    """Generates a detailed PDF feedback report for a single student."""

    @staticmethod
    def _get_styles():
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='h1_center', parent=styles['h1'], alignment=TA_CENTER))
        styles.add(ParagraphStyle(name='h2_center', parent=styles['h2'], alignment=TA_CENTER, spaceBefore=10, spaceAfter=10))
        styles.add(ParagraphStyle(name='h4_left', parent=styles['h4'], alignment=TA_LEFT, spaceBefore=10, spaceAfter=5))
        return styles

    @staticmethod
    def _handle_multimodal_content(content_blocks, story, styles):
        """Appends text and images from content blocks to the story. Robustly handles different data formats."""
        if not content_blocks:
            story.append(Paragraph("<i>No content provided.</i>", styles['BodyText']))
            return

        # Normalize content_blocks to always be a list of dictionaries
        if isinstance(content_blocks, str):
            normalized_blocks = [{'type': 'text', 'content': content_blocks}]
        elif isinstance(content_blocks, list):
            normalized_blocks = []
            for item in content_blocks:
                if isinstance(item, str):
                    normalized_blocks.append({'type': 'text', 'content': item})
                elif isinstance(item, dict) and 'type' in item and 'content' in item:
                    normalized_blocks.append(item)
            if not normalized_blocks:
                 story.append(Paragraph("<i>No content provided.</i>", styles['BodyText']))
                 return
        else:
            story.append(Paragraph("<i>[Unsupported content format]</i>", styles['BodyText']))
            return

        for block in normalized_blocks:
            content_type = block.get('type')
            content = block.get('content')
            if content_type == 'text' and content:
                story.append(Paragraph(content.replace('\n', '<br/>'), styles['BodyText']))
                story.append(Spacer(1, 0.1 * inch))
            elif content_type == 'image' and content:
                try:
                    img_data = io.BytesIO(content)
                    pil_img = PILImage.open(img_data)
                    
                    max_width = 5 * inch
                    if pil_img.width > max_width:
                        aspect_ratio = pil_img.height / pil_img.width
                        new_width = max_width
                        new_height = new_width * aspect_ratio
                        img = Image(img_data, width=new_width, height=new_height)
                    else:
                        img = Image(img_data, width=pil_img.width, height=pil_img.height)

                    story.append(img)
                    story.append(Spacer(1, 0.1 * inch))
                except Exception:
                    story.append(Paragraph("<i>[Could not display image]</i>", styles['BodyText']))

    @staticmethod
    def create_pdf(student_id: str, assignment_name: str, grading_data: list, total_score: float, total_possible: float) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2)
        styles = FeedbackPDFGenerator._get_styles()
        story = []

        # 1. Title Page
        story.append(Paragraph(f"Feedback Report", styles['h1_center']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"<b>Student:</b> {student_id}", styles['h2_center']))
        story.append(Paragraph(f"<b>Assignment:</b> {assignment_name}", styles['h2_center']))
        story.append(Spacer(1, 0.5 * inch))

        # 2. Summary Table
        story.append(Paragraph("Overall Score Summary", styles['h3']))
        summary_data = [['Question', 'Score']]
        for i, q_data in enumerate(grading_data):
            q_score = sum(r.get("score", 0) for r in q_data.get("rubric_scores", []))
            q_possible = sum(r.get("points", 0) for r in q_data.get("rubric_list", []))
            summary_data.append([Paragraph(f"Q{i+1}: {q_data['question'][:80]}...", styles['BodyText']), f"{q_score} / {q_possible}"])
        
        summary_data.append(['<b>TOTAL SCORE</b>', f"<b>{total_score} / {total_possible}</b>"])

        summary_table = Table(summary_data, colWidths=[4.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-2), colors.lightblue),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.darkblue),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(summary_table)
        story.append(PageBreak())

        # 3. Detailed Question Breakdown
        for i, q_data in enumerate(grading_data):
            story.append(Paragraph(f"Detailed Feedback for Question {i+1}", styles['h3']))
            story.append(Paragraph(f"<i>{q_data['question']}</i>", styles['Italic']))
            story.append(Spacer(1, 0.2 * inch))
            
            # Rubric Breakdown Table
            story.append(Paragraph("<b>Your Score Breakdown:</b>", styles['h4_left']))
            rubric_scores = q_data.get('rubric_scores', [])
            rubric_list = q_data.get('rubric_list', [])
            
            min_len = min(len(rubric_scores), len(rubric_list))
            
            rubric_data = [['Criterion', 'Your Score', 'Max Points']]
            for score_item, rubric_item in zip(rubric_scores[:min_len], rubric_list[:min_len]):
                rubric_data.append([Paragraph(rubric_item['criteria'], styles['BodyText']), score_item['score'], rubric_item['points']])
            
            q_score = sum(r.get("score", 0) for r in rubric_scores)
            q_possible = sum(r.get("points", 0) for r in rubric_list)
            rubric_data.append(['<b>Total for Question</b>', f'<b>{q_score}</b>', f'<b>{q_possible}</b>'])

            rubric_table = Table(rubric_data, colWidths=[4*inch, 1.25*inch, 1.25*inch])
            rubric_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(rubric_table)
            story.append(Spacer(1, 0.2 * inch))
            
            # AI Generated Feedback
            story.append(Paragraph("<b>Feedback & Explanation:</b>", styles['h4_left']))
            feedback_text = q_data.get('feedback', {}).get('text', 'No feedback was generated.')
            story.append(Paragraph(feedback_text.replace('\n', '<br/>'), styles['BodyText']))
            story.append(Spacer(1, 0.2 * inch))

            # Ideal Answer
            story.append(Paragraph("<b>Ideal Answer:</b>", styles['h4_left']))
            FeedbackPDFGenerator._handle_multimodal_content(q_data.get('ideal_answer', []), story, styles)
            story.append(Spacer(1, 0.2 * inch))
            
            # Student's Answer
            story.append(Paragraph("<b>Your Answer:</b>", styles['h4_left']))
            FeedbackPDFGenerator._handle_multimodal_content(q_data.get('student_answer_content', []), story, styles)
            
            if i < len(grading_data) - 1:
                story.append(PageBreak())
            
        doc.build(story)
        buffer.seek(0)
        return buffer
