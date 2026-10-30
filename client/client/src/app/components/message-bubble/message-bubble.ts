import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { ChatMsg } from '../../models/chat.models';

@Component({
  selector: 'app-message-bubble',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './message-bubble.html',
  styleUrl: './message-bubble.css',
})
export class MessageBubble {
  readonly message = input.required<ChatMsg>();

  readonly isUser = computed(() => this.message().role === 'user');
  readonly hour = computed(() => {
    const createdAt = this.message().createdAt;
    return createdAt ? createdAt.slice(11, 16) : '';
  });
}
