export var pixel_to_light = 1
export var blink_frequency_ms = 1500
var isBlinkingNow = 0
var currentBlinkDurationMs = 0

export function beforeRender(delta) {
  currentBlinkDurationMs = currentBlinkDurationMs + delta
  if (currentBlinkDurationMs > blink_frequency_ms) {
    currentBlinkDurationMs = 0
    isBlinkingNow = ! isBlinkingNow
  }
}

export function render(index) {
  if (isBlinkingNow && index == pixel_to_light) {
    hsv(0, 0, 1) 
  } else {
    hsv(0,0,0)
  }
}