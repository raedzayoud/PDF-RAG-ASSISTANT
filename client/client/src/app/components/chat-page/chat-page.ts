import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, ElementRef, computed, effect, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ChatMsg, SessionSummary } from '../../models/chat.models';
import { PdfChatApiService } from '../../services/pdf-chat-api.service';
import { MessageBubble } from '../message-bubble/message-bubble';

const SESSION_KEY = 'rag.sessionId';

@Component({
  selector: 'app-chat-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MessageBubble],
  templateUrl: './chat-page.html',
  styleUrl: './chat-page.css',
})
export class ChatPage {
  private readonly api = inject(PdfChatApiService);
  private readonly scroller = viewChild<ElementRef<HTMLElement>>('scroller');
  private readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  readonly sessions = signal<SessionSummary[]>([]);
  readonly activeSessionId = signal<string | null>(null);
  readonly messages = signal<ChatMsg[]>([]);
  readonly draft = signal('');
  readonly pending = signal(false);
  readonly uploading = signal(false);
  readonly syncing = signal(false);
  readonly toast = signal<{ kind: 'ok' | 'error'; text: string } | null>(null);
  readonly chatError = signal<string | null>(null);
  readonly dragging = signal(false);

  readonly busy = computed(() => this.pending() || this.uploading() || this.syncing());
  readonly activeTitle = computed(() => {
    const active = this.activeSessionId();
    const found = this.sessions().find((s) => s.session_id === active);
    if (!found) return 'Nouvelle discussion';
    return found.title ? found.title : 'Nouvelle discussion';
  });

  constructor() {
    this.bootstrap();
    effect(() => {
      if (this.messages().length || this.pending()) {
        setTimeout(() => {
          const el = this.scroller()?.nativeElement;
          if (el) el.scrollTop = el.scrollHeight;
        });
      }
    });
  }

  private async bootstrap(): Promise<void> {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved && (await this.openConversation(saved, true))) return;
    this.startNewDiscussion();
    await this.refreshSessions();
  }

  private async refreshSessions(): Promise<void> {
    try {
      this.sessions.set(await firstValueFrom(this.api.getSessions()));
    } catch (err) {
      if (err instanceof HttpErrorResponse && err.status === 0) {
        this.chatError.set(this.api.friendlyError(err));
      }
    }
  }

  startNewDiscussion(): void {
    this.activeSessionId.set(null);
    localStorage.removeItem(SESSION_KEY);
    this.messages.set([]);
    this.chatError.set(null);
  }

  async openConversation(sessionId: string, silent = false): Promise<boolean> {
    try {
      const rows = await firstValueFrom(this.api.messages(sessionId));
      this.activeSessionId.set(sessionId);
      localStorage.setItem(SESSION_KEY, sessionId);
      this.chatError.set(null);
      this.messages.set(
        rows.map((r) => ({
          id: r.id,
          role: r.role,
          content: r.content,
          createdAt: r.created_at,
        })),
      );
      await this.refreshSessions();
      return true;
    } catch (err) {
      if (!silent) {
        this.showToast('error', this.api.friendlyError(err));
      }
      if (err instanceof HttpErrorResponse && err.status === 404) {
        this.activeSessionId.set(null);
        localStorage.removeItem(SESSION_KEY);
        this.startNewDiscussion();
        await this.refreshSessions();
      }
      return false;
    }
  }

  async send(): Promise<void> {
    const question = this.draft().trim();
    if (!question || this.busy()) return;

    this.chatError.set(null);
    this.draft.set('');
    this.messages.update((list) => [...list, { role: 'user', content: question }]);
    this.pending.set(true);

    try {
      let session = this.activeSessionId();
      if (!session) {
        const created = await firstValueFrom(this.api.createSession());
        session = created.session_id;
        this.activeSessionId.set(session);
        localStorage.setItem(SESSION_KEY, session);
      }

      const res = await firstValueFrom(this.api.chat(session, question));
      this.messages.update((list) => [
        ...list,
        {
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          createdAt: new Date().toISOString(),
        },
      ]);
      await this.refreshSessions();
    } catch (err) {
      this.chatError.set(this.api.friendlyError(err));
      if (err instanceof HttpErrorResponse && err.status === 404) {
        this.startNewDiscussion();
        await this.refreshSessions();
      }
    } finally {
      this.pending.set(false);
    }
  }

  onInputKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void this.send();
    }
  }

  openFilePicker(): void {
    this.fileInput()?.nativeElement.click();
  }

  async onFilesChosen(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) void this.uploadAndIndex(file);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) void this.uploadAndIndex(file);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(true);
  }

  onDragLeave(): void {
    this.dragging.set(false);
  }

  private async uploadAndIndex(file: File): Promise<void> {
    const invalid = this.api.validatePdf(file);
    if (invalid) {
      this.showToast('error', invalid);
      return;
    }

    this.uploading.set(true);
    try {
      await firstValueFrom(this.api.uploadPdf(file));
      this.syncing.set(true);
      const sync = await firstValueFrom(this.api.syncDocuments());
      this.showToast('ok', `${file.name} indexé · ${sync.chunks} passages`);
    } catch (err) {
      this.showToast('error', this.api.friendlyError(err));
    } finally {
      this.uploading.set(false);
      this.syncing.set(false);
    }
  }

  private showToast(kind: 'ok' | 'error', text: string): void {
    this.toast.set({ kind, text });
    setTimeout(() => {
      if (this.toast()?.text === text) this.toast.set(null);
    }, 5000);
  }

  dayLabel(iso: string): string {
    const date = new Date(iso);
    const today = new Date();
    const same = date.toDateString() === today.toDateString();
    if (same) return date.toTimeString().slice(0, 5);
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
  }
}
