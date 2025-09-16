# 고급 성능 최적화 기법들 (필요시 참고용)

import time
from threading import Timer


class OptimizedDpsDistributionCanvas(FigureCanvas):
    """
    더 극단적인 성능 최적화가 필요한 경우 사용할 수 있는 기법들
    """

    def __init__(self, parent, data):
        super().__init__(parent, data)

        # 디바운싱을 위한 타이머
        self.hover_timer = None
        self.hover_delay = 0.016  # 약 60 FPS (16ms)

        # 마지막 업데이트 시간 추적
        self.last_update_time = 0

        # 블릿팅을 위한 배경 저장
        self.background = None

        # 애니메이션 모드 설정
        self.fig.canvas.toolbar_visible = False

    def plot(self):
        """기본 plot에 블릿팅 지원 추가"""
        super().plot()

        # 블릿팅을 위한 배경 캡처
        self.draw()
        self.background = self.fig.canvas.copy_from_bbox(self.ax.bbox)

    def on_hover_debounced(self, event):
        """디바운스된 호버 핸들러"""
        current_time = time.time()

        # 너무 빈번한 업데이트 방지 (60 FPS 제한)
        if current_time - self.last_update_time < self.hover_delay:
            return

        self.last_update_time = current_time
        self.on_hover(event)

    def on_hover_with_blit(self, event):
        """블릿팅을 사용한 고성능 호버 핸들러"""
        # ... 호버 로직 ...

        # 블릿팅을 사용한 빠른 업데이트
        if self.background:
            self.fig.canvas.restore_region(self.background)

            # 변경된 아티스트만 다시 그리기
            if self.bar_in_hover:
                self.ax.draw_artist(self.bar_in_hover)
            if self.annotation._visible:
                self.ax.draw_artist(self.annotation)

            self.fig.canvas.blit(self.ax.bbox)
        else:
            self.draw()

    def on_hover_throttled(self, event):
        """쓰로틀링을 사용한 호버 핸들러"""
        if self.hover_timer:
            self.hover_timer.cancel()

        self.hover_timer = Timer(self.hover_delay, lambda: self.on_hover(event))
        self.hover_timer.start()

    def update_with_animation(self):
        """애니메이션 프레임워크를 사용한 업데이트"""
        from matplotlib.animation import FuncAnimation

        def animate(frame):
            # 필요시 애니메이션 로직
            return []

        self.anim = FuncAnimation(self.fig, animate, interval=16, blit=True)


# 사용 예시:
# 1. 기본 최적화 (이미 적용됨)
# 2. 디바운싱: on_hover 대신 on_hover_debounced 사용
# 3. 블릿팅: on_hover 대신 on_hover_with_blit 사용
# 4. 쓰로틀링: on_hover 대신 on_hover_throttled 사용
