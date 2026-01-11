import pygame
import screens


class ValidatorAppGui:

    def __init__(self, config: dict, lang_strings: dict, status: dict):
        pygame.init()
        pygame.display.set_caption("Validator App")

        self.screen = pygame.display.set_mode(
            (config["screen_width"], config["screen_height"])
        )
        self.clock = pygame.time.Clock()

        self.splashscreen = screens.SplashScreen(self.screen, config)
        self.mainscreen = screens.MainScreen(self.screen, config, lang_strings, status)

        self.frame_count = 0
        self.running = True
        self.config = config
        self.status = status

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            if self.status["ready"]:
                self.mainscreen.update(self.frame_count)
            else:
                self.splashscreen.update(self.frame_count)

            self.frame_count += 1

            self.clock.tick(self.config["fps"])
            pygame.display.flip()

        pygame.quit()
