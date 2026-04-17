const CHUNK_SIZE = 60;
const OVERLAP = 10;

// Split source code into overlapping line-based chunks for embedding
export function chunkCode(content: string): string[] {
  const lines = content.split("\n");
  const chunks: string[] = [];

  for (let i = 0; i < lines.length; i += CHUNK_SIZE - OVERLAP) {
    const chunk = lines
      .slice(i, i + CHUNK_SIZE)
      .join("\n")
      .trim();
    if (chunk.length > 0) chunks.push(chunk);
  }

  return chunks;
}
