function collapseRepeatedOutput(text: string): string {
  const source = text.trim();
  if (source.length < 40) {
    return text;
  }

  const midpoint = Math.floor(source.length / 2);
  for (let offset = -4; offset <= 4; offset += 1) {
    const split = midpoint + offset;
    if (split <= 0 || split >= source.length) {
      continue;
    }
    const first = source.slice(0, split).trim();
    const second = source.slice(split).trim();
    if (first && first === second) {
      return first;
    }
  }
  return text;
}

export function normalizeFinalOutput(finalOutput: string, streamedOutput: string): string {
  return collapseRepeatedOutput(finalOutput || streamedOutput);
}
