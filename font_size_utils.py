from reportlab.pdfgen import canvas

# Function to calculate the maximum font size that fits both width and height
def calculate_font_size(text, coordinates):
    # Create a dummy canvas (no need to save a PDF, just to use stringWidth method)
    c = canvas.Canvas(None)

    # Extract the coordinates (x1, y1, x2, y2) from the given list
    x1, y1, x2, y2 = coordinates

    # Calculate the width and height of the box
    box_width = x2 - x1
    box_height = y2 - y1

    # Function to calculate the maximum font size based on both box width and height
    def get_max_font_size(text, box_width, box_height, font="Helvetica"):
        font_size = 10  # Start with a base font size
        max_font_size = 100  # Maximum font size to try

        # Calculate the maximum font size based on width
        while font_size <= max_font_size:
            text_width = c.stringWidth(text, font, font_size)
            if text_width > box_width:
                break
            font_size += 1
        font_size -= 1  # Subtract to avoid overflow in width

        # Now, calculate line height and total height of text for this font size
        lines = wrap_text(text, font, font_size, box_width)
        line_height = font_size + 2  # Space between lines
        total_text_height = len(lines) * line_height

        # If the total height exceeds the box height, reduce the font size
        while total_text_height > box_height and font_size > 1:
            font_size -= 1
            lines = wrap_text(text, font, font_size, box_width)
            total_text_height = len(lines) * line_height

        return font_size

    # Function to wrap the text within the box
    def wrap_text(text, font, font_size, box_width):
        lines = []
        current_line = []
        text_width = 0

        for word in text.split(" "):
            word_width = c.stringWidth(word, font, font_size)
            if text_width + word_width + c.stringWidth(" ", font, font_size) <= box_width:
                current_line.append(word)
                text_width += word_width + c.stringWidth(" ", font, font_size)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                text_width = word_width
        lines.append(" ".join(current_line))  # Add the last line
        return lines

    # Get the maximum font size based on both box width and height
    font_size = get_max_font_size(text, box_width, box_height)
    
    # Return the calculated font size
    return font_size