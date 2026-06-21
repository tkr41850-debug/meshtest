export function uptimeColor(percent: number): string {
  if (percent < 0) return "#e5e7eb";
  if (percent >= 0.999) return "hsl(120, 85%, 40%)";
  if (percent >= 0.9) {
    const t = (percent - 0.9) / (0.999 - 0.9);
    const hue = 45 + t * 75;
    return `hsl(${hue.toFixed(0)}, 85%, 40%)`;
  }
  return "hsl(0, 85%, 40%)";
}
