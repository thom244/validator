import datetime
import pygame


class Screen:
    changed = True

    def draw(self, frame_count: int):
        """Draw the screen"""
        pass

    def update(self, frame_count: int):
        """Update the screen"""
        if self.changed:
            self.draw(frame_count)
            self.changed = False


class SplashScreen(Screen):
    def __init__(
        self,
        surface: pygame.Surface,
        config: dict,
        text="Loading...",
        color=(255, 255, 255),
    ):
        self.surface = surface
        self.config = config

        self.splash_image = pygame.image.load("../images/splash_screen.png")
        self.font_large = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 24)

        self.text = text
        self.color = color

    def set_text(self, text):
        self.text = text
        self.changed = True

    def set_color(self, color):
        self.color = color
        self.changed = True

    def draw(self, frame_count: int):
        self.surface.blit(self.splash_image, (0, 0))
        loading_text = self.font_large.render(self.text, True, self.color)
        text_rect = loading_text.get_rect(
            center=(self.config["screen_width"] // 2, self.config["screen_height"] - 85)
        )
        self.surface.blit(loading_text, text_rect)


class MainScreen(Screen):
    background_color = (88, 188, 248)

    status_bar1_height = 30
    status_bar2_height = 28
    status_bar1_color = (32, 88, 152)
    status_bar2_color = (0, 120, 200)
    status_text_color = (255, 255, 255)
    status_separator_color = (248, 252, 248)
    status2_separator_color = (80, 84, 80)

    def __init__(self, surface: pygame.Surface, config: dict, lang: dict, status: dict):
        self.surface = surface
        self.config = config
        self.lang = lang
        self.status = status

        self.ui_surface = pygame.Surface(
            (self.config["screen_width"], self.config["screen_height"])
        )
        self.card_surface = pygame.Surface(
            (self.config["screen_width"], self.config["screen_height"]), pygame.SRCALPHA
        )

        self.background_image = pygame.image.load("../images/background.png")

        self.button_info = pygame.image.load("../images/button_info.png")
        self.button_plus = pygame.image.load("../images/button_plus.png")
        self.button_resp = pygame.image.load("../images/button_resp.png")

        self.banner_blue = pygame.image.load("../images/banner_blue.png")
        self.banner_green = pygame.image.load("../images/banner_green.png")
        self.banner_yellow = pygame.image.load("../images/banner_yellow.png")
        self.banner_red = pygame.image.load("../images/banner_red.png")

        self.card_img = pygame.image.load("../images/card.png")
        self.card_green_img = pygame.image.load("../images/card_green.png")
        self.card_red_img = pygame.image.load("../images/card_red.png")

        self.font_large = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 28)

    def draw_status_bar_1(self):
        surface = self.ui_surface
        bar_height = self.status_bar1_height
        bar_color = self.status_bar1_color
        separator_color = self.status_separator_color
        separator2_color = self.status2_separator_color

        pygame.draw.rect(
            surface,
            bar_color,
            pygame.Rect(0, 0, self.config["screen_width"], bar_height),
        )
        pygame.draw.rect(
            surface,
            separator_color,
            pygame.Rect(0, bar_height - 1, self.config["screen_width"], 1),
        )
        pygame.draw.rect(
            surface,
            separator2_color,
            pygame.Rect(0, bar_height - 2, self.config["screen_width"], 1),
        )

        operator_text = self.font_small.render(
            self.config.get("operator_name", ""), True, self.status_text_color
        )
        surface.blit(operator_text, (4, 6))

        date_text = self.font_small.render(
            datetime.datetime.now().strftime("%d.%m.%Y"), True, self.status_text_color
        )
        surface.blit(
            date_text,
            ((self.config["screen_width"] - date_text.get_width()) / 2, 6),
        )

        time_text = self.font_small.render(
            datetime.datetime.now().strftime("%H:%M"), True, self.status_text_color
        )
        surface.blit(
            time_text,
            (self.config["screen_width"] - time_text.get_width() - 4, 6),
        )

    def draw_status_bar_2(self):
        surface = self.ui_surface
        bar_offset = self.status_bar1_height
        bar_height = self.status_bar2_height
        bar_color = self.status_bar2_color
        separator_color = self.status_separator_color

        pygame.draw.rect(
            surface,
            bar_color,
            pygame.Rect(0, bar_offset, self.config["screen_width"], bar_height),
        )
        pygame.draw.rect(
            surface,
            separator_color,
            pygame.Rect(0, bar_offset + bar_height - 1, self.config["screen_width"], 1),
        )

        line_text = self.font_small.render(
            f"{self.lang.get('line_label', 'Line')} {self.config['line_name']}",
            True,
            self.status_text_color,
        )

        surface.blit(line_text, (4, bar_offset + 5))

    def draw_validation_status(self):
        bar_offset = self.status_bar1_height + self.status_bar2_height
        bar_height = 82
        bar_color = self.status_bar1_color

        pygame.draw.rect(
            self.ui_surface,
            bar_color,
            pygame.Rect(0, bar_offset, self.config["screen_width"], bar_height),
        )

        card_status = self.status.get("card_status")
        validation = self.status.get("last_validation", {})
        status = status2 = status3 = ""
        if card_status == "VALID":
            status = "Card validated for 1 trip"
            status2 = f"Remaining credits: {validation.get('credits', 0)}"
            status3 = f"Valid until: {validation.get('expiration_date', 'N/A')}"
        elif card_status == "INVALID":
            status2 = "Your card has been deactivated"
        elif card_status == "EXPIRED":
            status = "Your transit pass is expired"
            status2 = f"Expired on: {validation.get('expiration_date', 'N/A')}"
        elif card_status == "INSUFFICIENT_CREDITS":
            status = "You do not have enough credits"
            status2 = "Please recharge your card"

        status_text = self.font_small.render(status, True, self.status_text_color)
        self.ui_surface.blit(
            status_text,
            (4, bar_offset + 7),
        )

        status_text = self.font_small.render(status2, True, self.status_text_color)
        self.ui_surface.blit(
            status_text,
            (4, bar_offset + 7 + 26),
        )

        status_text = self.font_small.render(status3, True, self.status_text_color)
        self.ui_surface.blit(
            status_text,
            (4, bar_offset + 7 + 52),
        )

    def draw_buttons(self):
        surface = self.ui_surface

        button_y = self.status_bar1_height + self.status_bar2_height + 10

        surface.blit(self.button_resp, (10, button_y))
        surface.blit(
            self.button_plus,
            (
                (self.config["screen_width"] - self.button_plus.get_width()) // 2,
                button_y,
            ),
        )
        surface.blit(
            self.button_info,
            (
                self.config["screen_width"] - self.button_info.get_width() - 10,
                button_y,
            ),
        )

    def draw_banner(self):
        surface = self.ui_surface
        card_status = self.status.get("card_status")
        if card_status == "VALID":
            banner_img = self.banner_green
            banner_text = self.lang.get("have_a_nice_day", "Have a good trip!")
        elif card_status == "INVALID":
            banner_img = self.banner_red
            banner_text = self.lang.get("invalid_card", "Invalid card")
        elif card_status == "EXPIRED":
            banner_img = self.banner_red
            banner_text = self.lang.get("expired_card", "Expired card")
        elif card_status == "INSUFFICIENT_CREDITS":
            banner_img = self.banner_red
            banner_text = self.lang.get("insufficient_credits", "Insufficient credits")
        elif card_status == "LOADING":
            banner_img = self.banner_blue
            banner_text = self.lang.get("validating", "Validating card...")
        elif card_status == "UNKNOWN" or card_status == "TRY_AGAIN":
            banner_img = self.banner_red
            banner_text = self.lang.get("scan_card_again", "Try again")
        else:
            banner_img = self.banner_blue
            banner_text = self.lang.get("scan_card", "Scan your card")

        banner_y = self.config["screen_height"] - banner_img.get_height()
        surface.blit(banner_img, (0, banner_y))

        banner_text_surface = self.font_large.render(banner_text, True, (255, 255, 255))
        banner_text_x = (
            self.config["screen_width"] - banner_text_surface.get_width()
        ) // 2
        banner_text_y = (
            banner_y + (banner_img.get_height() - banner_text_surface.get_height()) // 2
        )
        surface.blit(banner_text_surface, (banner_text_x, banner_text_y))

    def draw_ui(self):
        self.ui_surface.blit(self.background_image, (0, 0))

        self.draw_status_bar_1()
        self.draw_status_bar_2()

        if self.status.get("card_status", "") in [
            "VALID",
            "INVALID",
            "EXPIRED",
            "INSUFFICIENT_CREDITS",
        ]:
            self.draw_validation_status()
        else:
            self.draw_buttons()

        self.draw_banner()

    def draw_card(self, frame_count: int):
        if self.status.get("card_active", False):
            opacity = 255
            card_status = self.status.get("card_status")
            if (
                card_status == "INVALID"
                or card_status == "EXPIRED"
                or card_status == "INSUFFICIENT_CREDITS"
            ):
                card_img = self.card_red_img
            elif card_status == "VALID":
                card_img = self.card_green_img
            else:
                card_img = self.card_img
        else:
            card_img = self.card_img
            duration = 10

            cycle_frame = frame_count % (duration * 3)

            if cycle_frame < duration:
                # Fade in
                opacity = int((cycle_frame / duration) * 255)
            elif cycle_frame < duration * 2:
                # Fully visible
                opacity = 255
            else:
                # Fade out
                opacity = int(((duration * 3 - cycle_frame) / duration) * 255)

        # Set opacity and draw card
        self.card_surface.fill((0, 0, 0, 0))
        card_img.set_alpha(opacity)
        card_x = (self.config["screen_width"] - card_img.get_width()) // 2
        card_y = 175
        self.card_surface.blit(card_img, (card_x, card_y))

    def draw(self, frame_count: int):
        self.surface.blit(self.ui_surface, (0, 0))
        self.surface.blit(self.card_surface, (0, 0))

    def update(self, frame_count: int):
        """Update the screen"""
        # if self.changed:
        #     self.draw_ui()
        #     self.changed = False

        self.draw_ui()
        self.draw_card(frame_count)

        self.draw(frame_count)
