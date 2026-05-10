export function altitudeColor(alt: number | null): string {
  if (alt == null) return '#94a3b8';
  if (alt >= 40000) return '#c084fc'; // purple
  if (alt >= 35000) return '#818cf8'; // indigo
  if (alt >= 30000) return '#38bdf8'; // sky blue
  if (alt >= 25000) return '#22d3ee'; // cyan
  if (alt >= 20000) return '#34d399'; // emerald
  if (alt >= 15000) return '#a3e635'; // lime
  if (alt >= 10000) return '#facc15'; // yellow
  if (alt >= 5000)  return '#fb923c'; // orange
  if (alt >= 2500)  return '#f87171'; // red
  return '#ef4444';
}

export const ALT_SCALE = [
  { label: '0',   color: '#ef4444' },
  { label: '5k',  color: '#fb923c' },
  { label: '10k', color: '#facc15' },
  { label: '15k', color: '#a3e635' },
  { label: '20k', color: '#34d399' },
  { label: '25k', color: '#22d3ee' },
  { label: '30k', color: '#38bdf8' },
  { label: '35k', color: '#818cf8' },
  { label: '40k+',color: '#c084fc' },
] as const;
