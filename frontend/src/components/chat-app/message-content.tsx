import DOMPurify from 'dompurify'

const TABLE_TAGS = ['table', 'thead', 'tbody', 'tr', 'th', 'td', 'colgroup', 'col']

/**
 * Split a line into cells. Supports:
 * - Pipe-separated: "col1 | col2 | col3"
 * - Tab-separated
 * - Multi-space separated (2+ spaces)
 */
function splitTableRow(line: string, preferPipe: boolean): string[] {
  const trimmed = line.trim()
  if (!trimmed) return []

  if (preferPipe && trimmed.includes('|')) {
    return trimmed.split('|').map((c) => c.trim())
  }
  // Split by tab or 2+ spaces
  return trimmed.split(/\t|\s{2,}/).map((c) => c.trim()).filter(Boolean)
}

/**
 * Detect if lines form a table. Returns preferred delimiter (pipe vs space) and parsed rows.
 * Strips optional [Table N] header line.
 */
function parseTableBlock(text: string): { rows: string[][]; preferPipe: boolean } | null {
  const stripped = text.replace(/^\[Table\s+\d+\]\s*\n?/, '').trim()
  const lines = stripped.split('\n').filter((line) => line.trim())
  if (lines.length < 2) return null

  const hasPipe = lines.some((l) => l.includes('|'))
  const preferPipe = hasPipe

  const rows: string[][] = []
  let colCount = 0
  for (const line of lines) {
    const cells = splitTableRow(line, preferPipe)
    if (cells.length < 2) return null
    if (colCount > 0 && cells.length !== colCount && Math.abs(cells.length - colCount) > 1) return null
    colCount = cells.length
    rows.push(cells)
  }
  return { rows, preferPipe }
}

/**
 * Convert table text (pipe, tab, or space-separated) to HTML table.
 */
function tableToHtml(text: string, compact = false): string {
  const parsed = parseTableBlock(text)
  if (!parsed) return ''

  const { rows } = parsed
  const cellClass = compact
    ? 'border border-white/20 px-2 py-1 text-xs'
    : 'border border-white/20 px-3 py-2'
  const headerClass = compact
    ? 'border border-white/20 bg-white/10 px-2 py-1 text-xs font-medium'
    : 'border border-white/20 bg-white/10 px-3 py-2 font-medium'

  let html = '<table class="min-w-full border-collapse border border-white/20 text-left text-sm table-auto">'
  rows.forEach((cells, i) => {
    const tag = i === 0 ? 'th' : 'td'
    const c = i === 0 ? headerClass : cellClass
    html += `<tr>${cells.map((cell) => `<${tag} class="${c}">${escapeHtml(cell)}</${tag}>`).join('')}</tr>`
  })
  html += '</table>'
  return html
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Find table blocks: [Table N] followed by lines, or consecutive lines with | or space-separated columns.
 */
function findTableBlocks(content: string): Array<{ start: number; end: number; text: string }> {
  const blocks: Array<{ start: number; end: number; text: string }> = []
  const lines = content.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    let blockStart = i
    let blockLines: string[] = []

    // Optional [Table N] header
    const tableHeaderMatch = line.match(/^(\[Table\s+\d+\])\s*$/)
    if (tableHeaderMatch) {
      blockLines.push(line)
      i++
      while (i < lines.length && lines[i].trim()) {
        blockLines.push(lines[i])
        i++
      }
    } else {
      // Look for consecutive lines that look like table rows (pipe or multi-column)
      const firstCells = splitTableRow(line, true)
      if (firstCells.length >= 2 || (splitTableRow(line, false).length >= 2 && line.trim().length > 10)) {
        blockLines.push(line)
        i++
        while (i < lines.length) {
          const nextCells = splitTableRow(lines[i], true)
          const nextSpaceCells = splitTableRow(lines[i], false)
          const isTableRow =
            (nextCells.length >= 2 && nextCells.length <= firstCells.length + 2) ||
            (nextSpaceCells.length >= 2 && line.includes('|') === false)
          if (!isTableRow || !lines[i].trim()) break
          blockLines.push(lines[i])
          i++
        }
      }
    }

    if (blockLines.length >= 2 && parseTableBlock(blockLines.join('\n'))) {
      blocks.push({
        start: content.split('\n').slice(0, blockStart).join('\n').length,
        end: content.split('\n').slice(0, i).join('\n').length,
        text: blockLines.join('\n'),
      })
    } else {
      i = blockStart + 1
    }
  }

  // Fallback: regex for pipe-separated blocks (catches any we missed)
  const pipeRegex = /(\[Table\s+\d+\]\s*\n)?([^\n]+\|[^\n]+(?:\n[^\n]+\|[^\n]+)+)/g
  let m
  while ((m = pipeRegex.exec(content)) !== null) {
    const start = m.index
    const end = m.index + m[0].length
    const overlaps = blocks.some((b) => start < b.end && end > b.start)
    if (!overlaps && parseTableBlock(m[2].trim())) {
      blocks.push({ start, end, text: m[2].trim() })
    }
  }

  return blocks.sort((a, b) => a.start - b.start)
}

/**
 * Parse content and convert table blocks (pipe, tab, or space-separated) to HTML tables.
 */
function processContent(content: string, compact = false): string {
  const blocks = findTableBlocks(content)
  if (blocks.length === 0) {
    return `<div class="whitespace-pre-wrap break-words">${escapeHtml(content.trim())}</div>`
  }

  const parts: string[] = []
  let lastEnd = 0

  for (const block of blocks) {
    const before = content.slice(lastEnd, block.start).trim()
    if (before) {
      parts.push(`<div class="whitespace-pre-wrap break-words">${escapeHtml(before)}</div>`)
    }
    const tableHtml = tableToHtml(block.text, compact)
    if (tableHtml) parts.push(tableHtml)
    lastEnd = block.end
  }

  const after = content.slice(lastEnd).trim()
  if (after) {
    parts.push(`<div class="whitespace-pre-wrap break-words">${escapeHtml(after)}</div>`)
  }

  return parts.length > 0 ? parts.join('\n\n') : `<div class="whitespace-pre-wrap break-words">${escapeHtml(content.trim())}</div>`
}

/**
 * Sanitize HTML, allowing only table-related tags and safe attributes.
 */
function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [...TABLE_TAGS, 'div', 'br', 'p', 'strong', 'em', 'b', 'i'],
    ALLOWED_ATTR: ['class', 'width'],
  })
}

export function MessageContent({
  content,
  compact = false,
}: {
  content: string
  compact?: boolean
}) {
  // Check if content already has HTML tables
  const hasHtmlTable = /<table[\s>]/i.test(content)

  let processed: string
  if (hasHtmlTable) {
    processed = content
  } else {
    processed = processContent(content, compact)
  }

  const sanitized = sanitizeHtml(processed)

  return (
    <div
      className={`prose prose-invert prose-sm max-w-none [&_table]:my-2 ${compact ? 'overflow-x-auto' : ''}`}
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  )
}
