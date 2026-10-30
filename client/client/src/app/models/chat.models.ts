export interface SessionInfo {
  session_id: string;
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  message_count: number;
  title: string | null;
}

export interface MessageRow {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface SourceRef {
  filename: string;
  page: number;
  similarity: number;
  snippet: string;
}

export interface DocStatus {
  ready: boolean;
  indexed_chunks: number;
}

export interface ChatResult {
  session_id: string;
  answer: string;
  sources: SourceRef[];
}

export interface ChatMsg {
  id?: number;
  role: 'user' | 'assistant' | 'pending';
  content: string;
  createdAt?: string;
  sources?: SourceRef[];
}

export interface UploadResult {
  filename: string;
  message: string;
}

export interface SyncResult {
  status: string;
  chunks: number;
}
