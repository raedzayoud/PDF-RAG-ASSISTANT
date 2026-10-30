import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import {
  ChatResult,
  DocStatus,
  MessageRow,
  SessionInfo,
  SessionSummary,
  SyncResult,
  UploadResult,
} from '../models/chat.models';

export const API_BASE_URL = 'http://127.0.0.1:8000';

const MAX_PDF_BYTES = 20 * 1024 * 1024;

@Injectable({ providedIn: 'root' })
export class PdfChatApiService {
  private readonly http = inject(HttpClient);

  status(): Observable<DocStatus> {
    return this.http.get<DocStatus>(`${API_BASE_URL}/api/documents/status`);
  }

  createSession(): Observable<SessionInfo> {
    return this.http.post<SessionInfo>(`${API_BASE_URL}/api/sessions`, {});
  }

  getSessions(limit = 50): Observable<SessionSummary[]> {
    return this.http.get<SessionSummary[]>(`${API_BASE_URL}/api/sessions?limit=${limit}`);
  }

  messages(sessionId: string, limit = 100): Observable<MessageRow[]> {
    return this.http.get<MessageRow[]>(
      `${API_BASE_URL}/api/sessions/${sessionId}/messages?limit=${limit}`,
    );
  }

  chat(sessionId: string, question: string): Observable<ChatResult> {
    return this.http.post<ChatResult>(`${API_BASE_URL}/api/chat`, {
      session_id: sessionId,
      question,
    });
  }

  uploadPdf(file: File): Observable<UploadResult> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<UploadResult>(`${API_BASE_URL}/api/documents/upload`, form);
  }

  syncDocuments(): Observable<SyncResult> {
    return this.http.post<SyncResult>(`${API_BASE_URL}/api/documents/sync`, {});
  }

  validatePdf(file: File): string | null {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return 'Seuls les fichiers .pdf sont acceptés.';
    }
    if (file.size > MAX_PDF_BYTES) {
      return 'PDF trop volumineux (20 Mo maximum).';
    }
    return null;
  }

  friendlyError(err: unknown): string {
    const e = err as HttpErrorResponse;
    switch (e?.status) {
      case 0:
        return 'API injoignable sur ' + API_BASE_URL + '. Vérifie que uvicorn (backend) tourne.';
      case 404:
        return 'Session introuvable ou index vide. Une nouvelle session a été créée, réessaie.';
      case 422: {
        const detail = (e.error as { detail?: unknown })?.detail;
        return typeof detail === 'string' ? detail : 'Requête invalide (422).';
      }
      case 502:
        return 'Le modèle LLM n\u2019a pas répondu. Vérifie la clé Groq, les quotas et les modèles.';
      case 503:
        return 'Aucun PDF indexé. Importe un PDF puis attends la fin de la réindexation.';
      case 413:
        return 'PDF trop volumineux pour le serveur (limite 20 Mo).';
      default:
        return 'Erreur inattendue (' + (e?.status ?? '?') + '). Consulte la console backend.';
    }
  }
}
