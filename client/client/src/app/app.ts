import { ChangeDetectionStrategy, Component } from '@angular/core';

import { ChatPage } from './components/chat-page/chat-page';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ChatPage],
  template: '<app-chat-page />',
})
export class App {}
