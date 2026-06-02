import { getApiUrl } from './client'
import type { SseEvent, Candidate, Citation, FinalEvent } from '../types'

export function connectStream(streamUrl: string): EventSource {
  const url = getApiUrl(streamUrl)
  return new EventSource(url)
}

export function connectStreamWithParser(
  streamUrl: string,
  onEvent: (event: SseEvent) => void,
  onError: (message: string) => void,
  onClose: () => void,
): EventSource {
  const url = getApiUrl(streamUrl)
  const es = new EventSource(url)

  es.addEventListener('candidates', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data)
      const candidates: Candidate[] = data.candidates ?? []
      onEvent({ type: 'candidates', candidates })
    } catch { /* ignore parse errors */ }
  })

  es.addEventListener('delta_text', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data)
      onEvent({ type: 'delta_text', text: data.text ?? '' })
    } catch { /* ignore */ }
  })

  es.addEventListener('citations', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data)
      const citations: Citation[] = data.citations ?? []
      onEvent({ type: 'citations', citations })
    } catch { /* ignore */ }
  })

  es.addEventListener('final', (e: MessageEvent) => {
    try {
      const finalEvent: FinalEvent = JSON.parse(e.data)
      onEvent({ type: 'final', event: finalEvent })
    } catch { /* ignore */ }
  })

  es.onerror = () => {
    onError('SSE 连接断开')
  }

  return es
}
