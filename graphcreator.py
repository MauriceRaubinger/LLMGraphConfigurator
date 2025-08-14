import pygame
import sys
import json
from collections import defaultdict
import os

# Initialize pygame
pygame.init()

# Constants - WHITE AND DARK BLUE THEME
WIDTH, HEIGHT = 1000, 700
TOOLBAR_HEIGHT = 60
NODE_WIDTH, NODE_HEIGHT = 120, 80
CONNECTOR_RADIUS = 8
BG_COLOR = (255, 255, 255)  # White background
TOOLBAR_COLOR = (240, 240, 245)  # Light gray toolbar
NODE_COLOR = (30, 60, 120)  # Dark blue
NODE_SELECTED_COLOR = (50, 100, 180)  # Lighter blue for selection
CONNECTOR_COLORS = ((70, 130, 180), (0, 191, 255))  # SteelBlue and DeepSkyBlue
CONNECTOR_HOVER_COLOR = (180, 220, 255)  # Light blue for hover
BUTTON_COLORS = [
    (50, 180, 100),  # MediumSeaGreen - retrieval
    (70, 130, 180),  # SteelBlue - input
    (220, 180, 60),  # GoldenRod - query
    (220, 100, 100),  # IndianRed - output
    (180, 100, 220),  # MediumOrchid - condition
    (100, 180, 180)  # Teal - memory (new color)
]
BUTTON_TYPES = ["input", "retrieval", "query", "output", "memory", "condition"]
TEXT_COLOR = (20, 20, 30)  # Almost black for text
LINE_COLOR = (30, 100, 200)  # Blue for connections
CONFIG_WINDOW_COLOR = (245, 245, 250)  # Very light gray
CONFIG_WINDOW_BORDER = (180, 180, 200)  # Light gray border
TEXT_INPUT_BG = (255, 255, 255)  # White
TEXT_INPUT_BORDER = (100, 130, 180)  # Blue border
DROP_ZONE_COLOR = (220, 230, 240)  # Very light blue
DROP_ZONE_HOVER = (200, 220, 240)  # Slightly darker blue
SCROLLBAR_COLOR = (180, 200, 220)  # Light blue for scrollbar
SCROLLBAR_HOVER = (150, 180, 210)  # Slightly darker for hover

# Configuration field descriptions
CONFIG_FIELDS = {
    "retrieval": ["Manual Injection"],
    "query": ["Behaviour"],
    "condition": ["Trigger"]
    # Add more node types as needed
}

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("LLMTSup Configurator")
font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 32)
text_font = pygame.font.SysFont(None, 22)

# Enable file dropping
pygame.event.set_allowed([pygame.DROPFILE])


class TextArea:
    def __init__(self, x, y, width, height, initial_text=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = initial_text
        self.lines = initial_text.split('\n') or [""]
        self.active = False
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_y = 0
        self.cursor_visible = True
        self.blink_timer = 0
        self.line_height = text_font.get_linesize()
        self.max_visible_lines = height // self.line_height
        self.scrollbar = pygame.Rect(x + width - 12, y, 10, height)
        self.scrollbar_knob = None
        self.dragging_scroll = False
        self.scroll_offset = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if clicked inside text area
            if self.rect.collidepoint(event.pos):
                self.active = True

                # Calculate cursor position based on click
                rel_x = event.pos[0] - self.rect.x
                rel_y = event.pos[1] - self.rect.y + self.scroll_y

                # Find line index
                self.cursor_y = min(len(self.lines) - 1, max(0, rel_y // self.line_height))

                # Find character position in line
                line_text = self.lines[self.cursor_y]
                char_width = 0
                self.cursor_x = 0

                for i, char in enumerate(line_text):
                    char_width += text_font.size(char)[0]
                    if char_width > rel_x:
                        break
                    self.cursor_x = i + 1

                return True

            # Check if clicked on scrollbar
            elif self.scrollbar_knob and self.scrollbar_knob.collidepoint(event.pos):
                self.dragging_scroll = True
                self.scroll_offset = event.pos[1] - self.scrollbar_knob.y
                return True
            else:
                self.active = False
                return False

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging_scroll = False
            return False

        elif event.type == pygame.MOUSEMOTION and self.dragging_scroll:
            # Handle scrollbar dragging
            knob_y = max(self.scrollbar.y, min(event.pos[1] - self.scroll_offset,
                                               self.scrollbar.y + self.scrollbar.height - self.scrollbar_knob.height))
            knob_rel_y = knob_y - self.scrollbar.y
            max_scroll = max(0, len(self.lines) * self.line_height - self.rect.height)
            # FIXED: Syntax error in this line
            if self.scrollbar_knob:
                max_knob_travel = self.scrollbar.height - self.scrollbar_knob.height
                if max_knob_travel > 0:
                    ratio = knob_rel_y / max_knob_travel
                    self.scroll_y = int(ratio * max_scroll)
            return True

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                # Split current line at cursor
                current_line = self.lines[self.cursor_y]
                new_line = current_line[self.cursor_x:]
                self.lines[self.cursor_y] = current_line[:self.cursor_x]
                self.lines.insert(self.cursor_y + 1, new_line)
                self.cursor_y += 1
                self.cursor_x = 0
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_x > 0:
                    # Delete character to the left
                    current_line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y] = current_line[:self.cursor_x - 1] + current_line[self.cursor_x:]
                    self.cursor_x -= 1
                elif self.cursor_y > 0:
                    # Merge with previous line
                    prev_line = self.lines[self.cursor_y - 1]
                    current_line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y - 1] = prev_line + current_line
                    del self.lines[self.cursor_y]
                    self.cursor_y -= 1
                    self.cursor_x = len(prev_line)
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_DELETE:
                if self.cursor_x < len(self.lines[self.cursor_y]):
                    # Delete character to the right
                    current_line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y] = current_line[:self.cursor_x] + current_line[self.cursor_x + 1:]
                elif self.cursor_y < len(self.lines) - 1:
                    # Merge with next line
                    current_line = self.lines[self.cursor_y]
                    next_line = self.lines[self.cursor_y + 1]
                    self.lines[self.cursor_y] = current_line + next_line
                    del self.lines[self.cursor_y + 1]
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_UP:
                if self.cursor_y > 0:
                    self.cursor_y -= 1
                    self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_DOWN:
                if self.cursor_y < len(self.lines) - 1:
                    self.cursor_y += 1
                    self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_LEFT:
                if self.cursor_x > 0:
                    self.cursor_x -= 1
                elif self.cursor_y > 0:
                    self.cursor_y -= 1
                    self.cursor_x = len(self.lines[self.cursor_y])
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_RIGHT:
                if self.cursor_x < len(self.lines[self.cursor_y]):
                    self.cursor_x += 1
                elif self.cursor_y < len(self.lines) - 1:
                    self.cursor_y += 1
                    self.cursor_x = 0
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_HOME:
                self.cursor_x = 0
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_END:
                self.cursor_x = len(self.lines[self.cursor_y])
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            elif event.key == pygame.K_TAB:
                # Insert 4 spaces for tab
                self.lines[self.cursor_y] = (self.lines[self.cursor_y][:self.cursor_x] +
                                             "    " +
                                             self.lines[self.cursor_y][self.cursor_x:])
                self.cursor_x += 4
                self.blink_timer = 0
                self.cursor_visible = True
                return True

            else:
                # Add regular character
                current_line = self.lines[self.cursor_y]
                self.lines[self.cursor_y] = (current_line[:self.cursor_x] +
                                             event.unicode +
                                             current_line[self.cursor_x:])
                self.cursor_x += len(event.unicode)
                self.blink_timer = 0
                self.cursor_visible = True
                return True

        return False

    def update(self):
        # Update cursor blink
        self.blink_timer += 1
        if self.blink_timer >= 30:
            self.blink_timer = 0
            self.cursor_visible = not self.cursor_visible

        # Update scrollbar knob
        total_height = len(self.lines) * self.line_height
        visible_height = self.rect.height

        if total_height > visible_height:
            knob_height = max(20, int((visible_height / total_height) * self.scrollbar.height))
            max_scroll = total_height - visible_height
            if max_scroll > 0:
                travel = self.scrollbar.height - knob_height
                knob_rel_y = (self.scroll_y / max_scroll) * travel
                knob_y = self.scrollbar.y + int(knob_rel_y)
            else:
                knob_y = self.scrollbar.y
            self.scrollbar_knob = pygame.Rect(self.scrollbar.x, knob_y, self.scrollbar.width, knob_height)
        else:
            self.scrollbar_knob = None
            self.scroll_y = 0

    def draw(self, surface):
        # Draw background
        pygame.draw.rect(surface, TEXT_INPUT_BG, self.rect)
        pygame.draw.rect(surface, TEXT_INPUT_BORDER if self.active else (180, 180, 200), self.rect, 2)

        # Draw scrollbar background
        pygame.draw.rect(surface, SCROLLBAR_COLOR, self.scrollbar)

        # Draw scrollbar knob if needed
        if self.scrollbar_knob:
            pygame.draw.rect(surface, SCROLLBAR_HOVER if self.dragging_scroll else SCROLLBAR_COLOR,
                             self.scrollbar_knob, 0, 5)
            pygame.draw.rect(surface, (100, 130, 180), self.scrollbar_knob, 1, 5)

        # Draw text lines
        clip_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width - 15, self.rect.height)
        surface.set_clip(clip_rect)

        y_pos = self.rect.y - self.scroll_y
        for i, line in enumerate(self.lines):
            if y_pos + self.line_height < self.rect.y:
                y_pos += self.line_height
                continue

            if y_pos > self.rect.y + self.rect.height:
                break

            text_surf = text_font.render(line, True, TEXT_COLOR)
            surface.blit(text_surf, (self.rect.x + 5, y_pos))

            # Draw cursor on active line
            if self.active and i == self.cursor_y and self.cursor_visible:
                cursor_text = line[:self.cursor_x]
                cursor_width = text_font.size(cursor_text)[0]
                cursor_y = y_pos + 2
                pygame.draw.line(surface, TEXT_COLOR,
                                 (self.rect.x + 5 + cursor_width, cursor_y),
                                 (self.rect.x + 5 + cursor_width, cursor_y + self.line_height - 4), 2)

            y_pos += self.line_height

        surface.set_clip(None)


class ConfigWindow:
    def __init__(self, node):
        self.node = node
        self.width = 500
        self.height = 400
        self.x = (WIDTH - self.width) // 2
        self.y = (HEIGHT - self.height) // 2
        self.visible = True
        self.drag_hover = False
        self.drag_file_path = None
        self.drag_error = None

        # Create configuration elements
        title = f"Configure {node.type} Node"
        self.title_text = title_font.render(title, True, TEXT_COLOR)

        # Get field descriptions for this node type
        self.field_descriptions = CONFIG_FIELDS.get(node.type, [])

        # Create text area fields
        self.inputs = []
        y_pos = self.y + 60

        # Initialize with node's content or empty strings
        content = node.content if node.content else [""] * len(self.field_descriptions)

        for i, desc in enumerate(self.field_descriptions):
            # Create description label
            desc_text = font.render(desc, True, (50, 80, 120))  # Dark blue text
            self.inputs.append(("label", desc_text, (self.x + 20, y_pos)))
            y_pos += desc_text.get_height() + 5

            # Create text area - with proper height for editing
            text_area = TextArea(self.x + 20, y_pos, self.width - 40, 120, content[i] if i < len(content) else "")
            self.inputs.append(("input", text_area))
            y_pos += 130  # 120 for height + 10 margin

        # Create drop zone for file drag-and-drop
        self.drop_zone = pygame.Rect(
            self.x + 20,
            y_pos + 10,
            self.width - 40,
            60
        )
        y_pos += 80

        # Adjust window height based on content
        self.height = max(self.height, y_pos - self.y + 60)

        # Create buttons
        button_width = 100
        button_height = 40
        self.save_button = pygame.Rect(
            self.x + self.width - button_width - 20,
            self.y + self.height - button_height - 20,
            button_width, button_height
        )
        self.cancel_button = pygame.Rect(
            self.x + 20,
            self.y + self.height - button_height - 20,
            button_width, button_height
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.save_button.collidepoint(event.pos):
                # Save configuration to node content
                text_values = []
                for item in self.inputs:
                    if item[0] == "input":
                        text_values.append('\n'.join(item[1].lines))
                self.node.content = text_values
                self.visible = False
                return True
            elif self.cancel_button.collidepoint(event.pos):
                self.visible = False
                return True
            else:
                for item in self.inputs:
                    if item[0] == "input":
                        if item[1].handle_event(event):
                            return True
        elif event.type == pygame.KEYDOWN:
            for item in self.inputs:
                if item[0] == "input":
                    if item[1].handle_event(event):
                        return True
        elif event.type == pygame.DROPFILE:
            file_path = event.file
            if file_path.endswith('.txt'):
                try:
                    with open(file_path, 'r') as f:
                        file_content = f.read()
                    # Store full content in node
                    if not self.node.content:
                        self.node.content = []
                    self.node.content.append(file_content)
                    self.drag_file_path = file_path
                    self.drag_error = None

                    # Update the text area
                    for item in self.inputs:
                        if item[0] == "input" and not item[1].text.strip():
                            item[1].text = file_content
                            item[1].lines = file_content.split('\n')
                            break
                except Exception as e:
                    self.drag_error = f"Error: {str(e)}"
            else:
                self.drag_error = "Only .txt files are supported"
            return True
        elif event.type == pygame.MOUSEMOTION:
            self.drag_hover = self.drop_zone.collidepoint(event.pos)
        return False

    def update(self):
        for item in self.inputs:
            if item[0] == "input":
                item[1].update()

    def draw(self, surface):
        pygame.draw.rect(surface, CONFIG_WINDOW_COLOR,
                         (self.x, self.y, self.width, self.height), 0, 10)
        pygame.draw.rect(surface, CONFIG_WINDOW_BORDER,
                         (self.x, self.y, self.width, self.height), 2, 10)

        surface.blit(self.title_text,
                     (self.x + (self.width - self.title_text.get_width()) // 2,
                      self.y + 20))

        for item in self.inputs:
            if item[0] == "label":
                surface.blit(item[1], item[2])
            elif item[0] == "input":
                item[1].draw(surface)

        drop_color = DROP_ZONE_HOVER if self.drag_hover else DROP_ZONE_COLOR
        pygame.draw.rect(surface, drop_color, self.drop_zone, 0, 8)
        pygame.draw.rect(surface, (150, 180, 210), self.drop_zone, 2, 8)

        drop_text = font.render("Drag & Drop .txt file here", True, (50, 80, 120))  # Dark blue text
        surface.blit(drop_text,
                     (self.drop_zone.centerx - drop_text.get_width() // 2,
                      self.drop_zone.centery - drop_text.get_height() // 2))

        if self.drag_file_path:
            file_text = font.render(f"Loaded: {self.drag_file_path}", True, (50, 150, 50))  # Green text
            surface.blit(file_text, (self.drop_zone.x + 5, self.drop_zone.y + self.drop_zone.height + 5))

        if self.drag_error:
            error_text = font.render(self.drag_error, True, (200, 50, 50))  # Red text
            surface.blit(error_text, (self.drop_zone.x + 5, self.drop_zone.y + self.drop_zone.height + 5))

        pygame.draw.rect(surface, (80, 180, 80), self.save_button, 0, 8)
        pygame.draw.rect(surface, (180, 80, 80), self.cancel_button, 0, 8)

        save_text = font.render("Save", True, TEXT_COLOR)
        cancel_text = font.render("Cancel", True, TEXT_COLOR)

        surface.blit(save_text,
                     (self.save_button.centerx - save_text.get_width() // 2,
                      self.save_button.centery - save_text.get_height() // 2))

        surface.blit(cancel_text,
                     (self.cancel_button.centerx - cancel_text.get_width() // 2,
                      self.cancel_button.centery - cancel_text.get_height() // 2))


class Node:
    def __init__(self, node_id, node_type, x, y):
        self.id = node_id
        self.type = node_type
        self.x = x
        self.y = y
        self.width = NODE_WIDTH
        self.height = NODE_HEIGHT
        self.input_connector = (x, y + self.height // 2)
        self.output_connector = (x + self.width, y + self.height // 2)
        # Additional outputs for condition node
        self.true_output = (x + self.width, y + self.height // 3) if node_type == "condition" else None
        self.false_output = (x + self.width, y + 2 * self.height // 3) if node_type == "condition" else None
        self.selected = False
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.content = []  # List to store configuration content

        # Configuration button for non-input/output nodes
        self.config_button = pygame.Rect(
            self.x + self.width - 25,
            self.y + 5,
            20, 20
        ) if self.type not in ["input", "output", "memory"] else None  # Added memory to exclusion

    def draw(self, surface, camera_offset_x, camera_offset_y):
        # Convert world coordinates to screen coordinates
        screen_x = self.x - camera_offset_x
        screen_y = self.y - camera_offset_y

        # Get the fill color based on node type
        fill_color = BUTTON_COLORS[BUTTON_TYPES.index(self.type)]

        # Draw node body
        pygame.draw.rect(surface, fill_color,
                         (screen_x, screen_y, self.width, self.height), 0, 10)

        # Draw border - darker for selected nodes
        border_color = NODE_SELECTED_COLOR if self.selected else (max(0, fill_color[0] - 40),
                                                                  max(0, fill_color[1] - 40),
                                                                  max(0, fill_color[2] - 40))
        pygame.draw.rect(surface, border_color,
                         (screen_x, screen_y, self.width, self.height), 2, 10)

        # Draw connectors
        if self.type != "input":
            input_connector_screen = (self.input_connector[0] - camera_offset_x,
                                      self.input_connector[1] - camera_offset_y)
            pygame.draw.circle(surface, CONNECTOR_COLORS[0], input_connector_screen, CONNECTOR_RADIUS)
            pygame.draw.circle(surface, (30, 80, 140), input_connector_screen, CONNECTOR_RADIUS, 2)

        if self.type != "output":
            # For condition node, draw two outputs
            if self.type == "condition":
                true_output_screen = (self.true_output[0] - camera_offset_x,
                                      self.true_output[1] - camera_offset_y)
                false_output_screen = (self.false_output[0] - camera_offset_x,
                                       self.false_output[1] - camera_offset_y)

                pygame.draw.circle(surface, (0, 255, 0), true_output_screen, CONNECTOR_RADIUS)
                pygame.draw.circle(surface, (0, 140, 210), true_output_screen, CONNECTOR_RADIUS, 2)

                pygame.draw.circle(surface, (255, 0, 0), false_output_screen, CONNECTOR_RADIUS)
                pygame.draw.circle(surface, (0, 140, 210), false_output_screen, CONNECTOR_RADIUS, 2)
            else:
                output_connector_screen = (self.output_connector[0] - camera_offset_x,
                                           self.output_connector[1] - camera_offset_y)
                pygame.draw.circle(surface, CONNECTOR_COLORS[1], output_connector_screen, CONNECTOR_RADIUS)
                pygame.draw.circle(surface, (0, 140, 210), output_connector_screen, CONNECTOR_RADIUS, 2)

        # Draw node label
        type_text = font.render(self.type, True, TEXT_COLOR)
        surface.blit(type_text, (screen_x + 10, screen_y + self.height // 2 - 10))

        # Draw configuration button for non-input/output nodes
        if self.config_button:
            config_button_screen = pygame.Rect(
                self.config_button.x - camera_offset_x,
                self.config_button.y - camera_offset_y,
                self.config_button.width,
                self.config_button.height
            )
            pygame.draw.rect(surface, (100, 180, 255), config_button_screen, 0, 5)  # Light blue button
            config_text = font.render("C", True, TEXT_COLOR)
            surface.blit(config_text,
                         (config_button_screen.centerx - config_text.get_width() // 2,
                          config_button_screen.centery - config_text.get_height() // 2))

    def update_connectors(self):
        self.input_connector = (self.x, self.y + self.height // 2)
        self.output_connector = (self.x + self.width, self.y + self.height // 2)

        # Update condition node outputs
        if self.type == "condition":
            self.true_output = (self.x + self.width, self.y + self.height // 3)
            self.false_output = (self.x + self.width, self.y + 2 * self.height // 3)

        # Update config button position
        if self.config_button:
            self.config_button.x = self.x + self.width - 25
            self.config_button.y = self.y + 5

    def contains_point(self, point, camera_offset_x, camera_offset_y):
        # Convert world point to screen point for comparison
        screen_x = self.x - camera_offset_x
        screen_y = self.y - camera_offset_y
        return (screen_x <= point[0] <= screen_x + self.width and
                screen_y <= point[1] <= screen_y + self.height)

    def input_contains_point(self, point, camera_offset_x, camera_offset_y):
        input_connector_screen = (self.input_connector[0] - camera_offset_x,
                                  self.input_connector[1] - camera_offset_y)
        dx = point[0] - input_connector_screen[0]
        dy = point[1] - input_connector_screen[1]
        return dx * dx + dy * dy <= CONNECTOR_RADIUS * CONNECTOR_RADIUS

    def output_contains_point(self, point, camera_offset_x, camera_offset_y):
        # Check all outputs for condition node
        if self.type == "condition":
            true_output_screen = (self.true_output[0] - camera_offset_x,
                                  self.true_output[1] - camera_offset_y)
            false_output_screen = (self.false_output[0] - camera_offset_x,
                                   self.false_output[1] - camera_offset_y)

            dx1 = point[0] - true_output_screen[0]
            dy1 = point[1] - true_output_screen[1]
            dx2 = point[0] - false_output_screen[0]
            dy2 = point[1] - false_output_screen[1]
            return (dx1 * dx1 + dy1 * dy1 <= CONNECTOR_RADIUS * CONNECTOR_RADIUS or
                    dx2 * dx2 + dy2 * dy2 <= CONNECTOR_RADIUS * CONNECTOR_RADIUS)
        elif self.type != "output":
            output_connector_screen = (self.output_connector[0] - camera_offset_x,
                                       self.output_connector[1] - camera_offset_y)
            dx = point[0] - output_connector_screen[0]
            dy = point[1] - output_connector_screen[1]
            return dx * dx + dy * dy <= CONNECTOR_RADIUS * CONNECTOR_RADIUS
        return False

    def get_output_at_point(self, point, camera_offset_x, camera_offset_y):
        """Returns which output connector is at the point (for condition nodes)"""
        if self.type == "condition":
            true_output_screen = (self.true_output[0] - camera_offset_x,
                                  self.true_output[1] - camera_offset_y)
            false_output_screen = (self.false_output[0] - camera_offset_x,
                                   self.false_output[1] - camera_offset_y)

            dx1 = point[0] - true_output_screen[0]
            dy1 = point[1] - true_output_screen[1]
            if dx1 * dx1 + dy1 * dy1 <= CONNECTOR_RADIUS * CONNECTOR_RADIUS:
                return "true"

            dx2 = point[0] - false_output_screen[0]
            dy2 = point[1] - false_output_screen[1]
            if dx2 * dx2 + dy2 * dy2 <= CONNECTOR_RADIUS * CONNECTOR_RADIUS:
                return "false"
        elif self.type != "output":
            output_connector_screen = (self.output_connector[0] - camera_offset_x,
                                       self.output_connector[1] - camera_offset_y)
            dx = point[0] - output_connector_screen[0]
            dy = point[1] - output_connector_screen[1]
            if dx * dx + dy * dy <= CONNECTOR_RADIUS * CONNECTOR_RADIUS:
                return "output"
        return None

    def config_button_contains_point(self, point, camera_offset_x, camera_offset_y):
        if not self.config_button:
            return False
        config_button_screen = pygame.Rect(
            self.config_button.x - camera_offset_x,
            self.config_button.y - camera_offset_y,
            self.config_button.width,
            self.config_button.height
        )
        return config_button_screen.collidepoint(point)


class Connection:
    def __init__(self, from_node, to_node, output_type="output"):
        self.from_node = from_node
        self.to_node = to_node
        self.output_type = output_type  # For condition nodes: "true" or "false"

    def draw(self, surface, camera_offset_x, camera_offset_y):
        # Determine start position based on output type
        if self.from_node.type == "condition":
            if self.output_type == "true":
                start_pos = self.from_node.true_output
            else:  # "false"
                start_pos = self.from_node.false_output
        else:
            start_pos = self.from_node.output_connector

        end_pos = self.to_node.input_connector

        # Convert to screen coordinates
        start_pos = (start_pos[0] - camera_offset_x, start_pos[1] - camera_offset_y)
        end_pos = (end_pos[0] - camera_offset_x, end_pos[1] - camera_offset_y)

        # Draw a bezier curve for the connection line
        control_point1 = (start_pos[0] + 50, start_pos[1])
        control_point2 = (end_pos[0] - 50, end_pos[1])

        # Draw multiple segments to create a smooth curve
        for i in range(20):
            t1 = i / 20
            t2 = (i + 1) / 20

            # Calculate points on the curve
            x1 = (1 - t1) ** 3 * start_pos[0] + 3 * (1 - t1) ** 2 * t1 * control_point1[0] + 3 * (1 - t1) * t1 ** 2 * \
                 control_point2[0] + t1 ** 3 * end_pos[0]
            y1 = (1 - t1) ** 3 * start_pos[1] + 3 * (1 - t1) ** 2 * t1 * control_point1[1] + 3 * (1 - t1) * t1 ** 2 * \
                 control_point2[1] + t1 ** 3 * end_pos[1]

            x2 = (1 - t2) ** 3 * start_pos[0] + 3 * (1 - t2) ** 2 * t2 * control_point1[0] + 3 * (1 - t2) * t2 ** 2 * \
                 control_point2[0] + t2 ** 3 * end_pos[0]
            y2 = (1 - t2) ** 3 * start_pos[1] + 3 * (1 - t2) ** 2 * t2 * control_point1[1] + 3 * (1 - t2) * t2 ** 2 * \
                 control_point2[1] + t2 ** 3 * end_pos[1]

            pygame.draw.line(surface, LINE_COLOR, (x1, y1), (x2, y2), 2)

        # Draw arrowhead at the end
        direction = pygame.math.Vector2(end_pos[0] - control_point2[0], end_pos[1] - control_point2[1])
        if direction.length() > 0:
            direction.scale_to_length(10)
            arrow_left = pygame.math.Vector2(-direction.y, direction.x) * 0.3
            arrow_right = pygame.math.Vector2(direction.y, -direction.x) * 0.3

            arrow_points = [
                end_pos,
                (end_pos[0] - direction.x + arrow_left.x, end_pos[1] - direction.y + arrow_left.y),
                (end_pos[0] - direction.x + arrow_right.x, end_pos[1] - direction.y + arrow_right.y)
            ]

            pygame.draw.polygon(surface, LINE_COLOR, arrow_points)


class Graph:
    def __init__(self):
        self.nodes = []
        self.connections = []
        self.next_node_id = 1

    def add_node(self, node_type, x, y):
        new_node = Node(self.next_node_id, node_type, x - 23, y + 70)
        self.nodes.append(new_node)
        self.next_node_id += 1
        return new_node

    def add_connection(self, from_node, to_node, output_type="output"):
        # Check if connection already exists
        for connection in self.connections:
            if (connection.from_node == from_node and
                    connection.to_node == to_node and
                    connection.output_type == output_type):
                return

        new_connection = Connection(from_node, to_node, output_type)
        self.connections.append(new_connection)

    def remove_node(self, node):
        # Remove all connections involving this node
        self.connections = [conn for conn in self.connections
                            if conn.from_node != node and conn.to_node != node]
        self.nodes.remove(node)

    def get_node_at(self, pos, camera_offset_x, camera_offset_y):
        for node in reversed(self.nodes):  # Check from top (last drawn) to bottom
            if node.contains_point(pos, camera_offset_x, camera_offset_y):
                return node
        return None

    def get_input_connector_at(self, pos, camera_offset_x, camera_offset_y):
        for node in reversed(self.nodes):
            if node.input_contains_point(pos, camera_offset_x, camera_offset_y):
                return node
        return None

    def get_output_connector_at(self, pos, camera_offset_x, camera_offset_y):
        for node in reversed(self.nodes):
            if node.output_contains_point(pos, camera_offset_x, camera_offset_y):
                return node
        return None

    def to_dict(self):
        """Convert the graph to a dictionary for serialization"""
        graph_dict = {
            "nodes": [],
            "connections": []
        }

        node_id_map = {}
        for i, node in enumerate(self.nodes):
            node_id_map[node] = node.id
            graph_dict["nodes"].append({
                "id": node.id,
                "type": node.type,
                "content": node.content
            })

        for conn in self.connections:
            graph_dict["connections"].append({
                "from": node_id_map[conn.from_node],
                "to": node_id_map[conn.to_node],
                "output_type": conn.output_type
            })

        return graph_dict

    def from_dict(self, graph_dict):
        """Load the graph from a dictionary"""
        self.nodes = []
        self.connections = []

        node_id_map = {}
        for node_data in graph_dict["nodes"]:
            node = Node(node_data["id"], node_data["type"])
            node.content = node_data.get("content", [])
            self.nodes.append(node)
            node_id_map[node_data["id"]] = node
            if node.id >= self.next_node_id:
                self.next_node_id = node.id + 1

        for conn_data in graph_dict["connections"]:
            from_node = node_id_map[conn_data["from"]]
            to_node = node_id_map[conn_data["to"]]
            output_type = conn_data.get("output_type", "output")
            self.add_connection(from_node, to_node, output_type)


class Button:
    def __init__(self, x, y, width, height, text, color, node_type=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.node_type = node_type
        self.hovered = False

    def draw(self, surface):
        color = self.color
        if self.hovered:
            # Lighten the color when hovered
            color = tuple(min(c + 40, 255) for c in self.color)

        pygame.draw.rect(surface, color, self.rect, 0, 8)
        pygame.draw.rect(surface, (180, 180, 200), self.rect, 2, 8)  # Light gray border

        text_surf = font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def contains_point(self, point):
        return self.rect.collidepoint(point)


def draw_toolbar(surface, buttons):
    pygame.draw.rect(surface, TOOLBAR_COLOR, (0, 0, WIDTH, TOOLBAR_HEIGHT))

    # Draw title
    title = title_font.render("LLMTSup", True, BUTTON_COLORS[1])
    surface.blit(title, (20, TOOLBAR_HEIGHT // 2 - title.get_height() // 2))

    # Draw buttons
    for button in buttons:
        button.draw(surface)


def draw_connection_preview(surface, start_pos, end_pos):
    pygame.draw.line(surface, LINE_COLOR, start_pos, end_pos, 2)

    # Draw temporary connectors
    pygame.draw.circle(surface, CONNECTOR_HOVER_COLOR, start_pos, CONNECTOR_RADIUS)
    pygame.draw.circle(surface, CONNECTOR_HOVER_COLOR, end_pos, CONNECTOR_RADIUS)


def draw_graph_info(surface, graph):
    info_text = [
        f"Nodes: {len(graph.nodes)}",
        f"Connections: {len(graph.connections)}"
    ]

    y_pos = TOOLBAR_HEIGHT + 10
    for text in info_text:
        text_surf = font.render(text, True, (50, 80, 120))  # Dark blue text
        surface.blit(text_surf, (WIDTH - text_surf.get_width() - 20, y_pos))
        y_pos += text_surf.get_height() + 5


def save_graph_screenshot(surface, file_path):
    """Save a screenshot of the graph area"""
    # Create a surface for the graph area (excluding toolbar and help text)
    graph_area = pygame.Rect(0, TOOLBAR_HEIGHT, WIDTH, HEIGHT - TOOLBAR_HEIGHT - 150)
    graph_surface = pygame.Surface((graph_area.width, graph_area.height))
    graph_surface.blit(surface, (0, 0), graph_area)

    # Save to file
    pygame.image.save(graph_surface, file_path)
    print(f"Graph image saved to {file_path}")


def main():
    graph = Graph()

    # Camera offset for panning
    camera_offset_x = 0
    camera_offset_y = 0
    panning = False
    pan_start_x = 0
    pan_start_y = 0

    # Create toolbar buttons
    buttons = [
        Button(140, 10, 88, 40, "Input", BUTTON_COLORS[0], "input"),
        Button(230, 10, 88, 40, "Retrieval", BUTTON_COLORS[1], "retrieval"),
        Button(320, 10, 88, 40, "LLM-Query", BUTTON_COLORS[2], "query"),
        Button(410, 10, 88, 40, "Condition", BUTTON_COLORS[4], "condition"),
        Button(500, 10, 88, 40, "Memory", BUTTON_COLORS[5], "memory"),
        Button(590, 10, 88, 40, "Output", BUTTON_COLORS[3], "output"),
    ]

    # Create a save/load button
    save_button = Button(WIDTH - 250, 10, 110, 40, "Save Graph", BUTTON_COLORS[1])
    load_button = Button(WIDTH - 130, 10, 110, 40, "Clear all", (180, 100, 100))
    buttons.extend([save_button, load_button])

    # State variables
    dragging_node = None
    connecting_start = None
    connecting_start_output = None
    connecting_end = None
    selected_node = None
    config_window = None
    input_exists = False

    clock = pygame.time.Clock()

    while True:
        mouse_pos = pygame.mouse.get_pos()

        # Convert mouse position to world coordinates for graph interactions
        world_mouse_pos = (mouse_pos[0] + camera_offset_x, mouse_pos[1] + camera_offset_y)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Handle file drops
            if event.type == pygame.DROPFILE and config_window and config_window.visible:
                config_window.handle_event(event)

            # If a configuration window is open, let it handle events first
            if config_window and config_window.visible:
                if config_window.handle_event(event):
                    # If the event was handled, don't process it further
                    continue
                # If the window handled the event but didn't close, we still skip other processing
                if config_window.visible:
                    continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check if clicked on a toolbar button
                for button in buttons:
                    if button.contains_point(mouse_pos):
                        if button == save_button:
                            # Save graph to file
                            json_file = "graph.json"
                            with open(json_file, "w") as f:
                                json.dump(graph.to_dict(), f, indent=2)
                            print(f"Graph saved to {json_file}")

                            # Save screenshot
                            screenshot_file = os.path.splitext(json_file)[0] + ".png"
                            save_graph_screenshot(screen, screenshot_file)
                        elif button == load_button:
                            # Clear the graph
                            print(graph.nodes)
                            selected_node = None
                            graph.nodes = []
                            graph.connections = []
                            input_exists = False
                        elif button.node_type:
                            # Create a new node
                            if not button.node_type == "input" or (button.node_type == "input" and not input_exists):
                                new_node = graph.add_node(button.node_type, world_mouse_pos[0], world_mouse_pos[1])
                                selected_node = new_node
                                for node in graph.nodes:
                                    node.selected = (node == new_node)

                                if button.node_type == "input":
                                    input_exists = True
                        break
                else:
                    # Check if clicked on background for panning
                    if not any(button.contains_point(mouse_pos) for button in buttons) and \
                            not graph.get_node_at(mouse_pos, camera_offset_x, camera_offset_y) and \
                            not connecting_start and \
                            (config_window is None or not config_window.visible):
                        panning = True
                        pan_start_x = mouse_pos[0]
                        pan_start_y = mouse_pos[1]

                    # Check if clicked on a node's config button
                    for node in graph.nodes:
                        if node.config_button and node.config_button_contains_point(mouse_pos, camera_offset_x,
                                                                                    camera_offset_y):
                            # Open configuration window for this node
                            config_window = ConfigWindow(node)
                            break

                    # Check if clicked on a node connector
                    output_node = graph.get_output_connector_at(mouse_pos, camera_offset_x, camera_offset_y)
                    if output_node:
                        connecting_start = output_node
                        connecting_start_output = output_node.get_output_at_point(mouse_pos, camera_offset_x,
                                                                                  camera_offset_y)
                        connecting_end = mouse_pos
                        continue

                    # Check if clicked on a node
                    clicked_node = graph.get_node_at(mouse_pos, camera_offset_x, camera_offset_y)
                    if event.button == 3:  # Right mouse button
                        if clicked_node:
                            # Handle right-click for deletion
                            if clicked_node.type == "input":
                                input_exists = False
                            graph.remove_node(clicked_node)
                            if clicked_node == selected_node:
                                selected_node = None
                    elif clicked_node:
                        # Select node and start dragging
                        if not config_window or (config_window and not config_window.visible):
                            dragging_node = clicked_node
                            dragging_node.dragging = True
                            dragging_node.drag_offset_x = world_mouse_pos[0] - dragging_node.x
                            dragging_node.drag_offset_y = world_mouse_pos[1] - dragging_node.y

                        # Deselect other nodes
                        for node in graph.nodes:
                            node.selected = (node == dragging_node)
                        selected_node = dragging_node
                    else:
                        # Clicked on empty space - deselect all
                        for node in graph.nodes:
                            node.selected = False
                        selected_node = None

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging_node:
                    dragging_node.dragging = False
                    dragging_node = None

                if connecting_start and connecting_end:
                    # Check if released on an input connector
                    input_node = graph.get_input_connector_at(mouse_pos, camera_offset_x, camera_offset_y)
                    if input_node and input_node != connecting_start and input_node.type != "input":
                        graph.add_connection(connecting_start, input_node, connecting_start_output)

                    connecting_start = None
                    connecting_start_output = None
                    connecting_end = None

                if panning:
                    panning = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DELETE and selected_node:
                    graph.remove_node(selected_node)
                    selected_node = None

        # Handle dragging
        if dragging_node:
            dragging_node.x = world_mouse_pos[0] - dragging_node.drag_offset_x
            dragging_node.y = world_mouse_pos[1] - dragging_node.drag_offset_y
            dragging_node.update_connectors()

        # Handle panning
        if panning:
            dx = mouse_pos[0] - pan_start_x
            dy = mouse_pos[1] - pan_start_y
            camera_offset_x -= dx
            camera_offset_y -= dy
            pan_start_x = mouse_pos[0]
            pan_start_y = mouse_pos[1]

        # Update connection preview
        if connecting_start:
            connecting_end = mouse_pos

        # Update button hover states
        for button in buttons:
            button.hovered = button.contains_point(mouse_pos)

        # Update config window if open
        if config_window and config_window.visible:
            config_window.update()

        # Draw everything
        screen.fill(BG_COLOR)

        # Draw connections
        for connection in graph.connections:
            connection.draw(screen, camera_offset_x, camera_offset_y)

        # Draw connection preview if in progress
        if connecting_start and connecting_end:
            # Determine start position based on output type
            if connecting_start.type == "condition":
                if connecting_start_output == "true":
                    start_pos = connecting_start.true_output
                else:  # "false"
                    start_pos = connecting_start.false_output
            else:
                start_pos = connecting_start.output_connector

            # Convert start position to screen coordinates
            start_pos_screen = (start_pos[0] - camera_offset_x, start_pos[1] - camera_offset_y)
            draw_connection_preview(screen, start_pos_screen, connecting_end)

        # Draw nodes
        for node in graph.nodes:
            node.draw(screen, camera_offset_x, camera_offset_y)

        # Draw toolbar
        draw_toolbar(screen, buttons)

        # Draw graph info
        draw_graph_info(screen, graph)

        # Draw configuration window if open
        if config_window and config_window.visible:
            config_window.draw(screen)

        # Draw help text
        help_text = [
            "Left-click: Select/Move nodes",
            "Right-click: Delete nodes",
            "Drag from output to input: Create connection",
            "'C' button: Configure node",
            "In config window: Drag & drop .txt files",
            "Condition nodes have two outputs: true and false",
            "Click and drag background to pan",
            "Text editing: Use arrow keys, enter, backspace, etc."
        ]

        y_pos = HEIGHT - 150
        for text in help_text:
            text_surf = font.render(text, True, (50, 80, 120))  # Dark blue text
            screen.blit(text_surf, (20, y_pos))
            y_pos += 25

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()