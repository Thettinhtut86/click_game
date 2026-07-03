import {
  Component,
  ElementRef,
  HostListener,
  ViewChild,
  OnInit,
  OnDestroy
} from '@angular/core';
import { WebSocket } from '../../services/web-socket';
import { Router } from '@angular/router';

@Component({
  selector: 'app-chat',
  standalone: false,
  templateUrl: './chat.html',
  styleUrl: './chat.css'
})
export class Chat {

  messages: any[] = [];

  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;
  token = sessionStorage.getItem('token')!;

  onlineUsers: any[] = [];

  @ViewChild('chatBox') chatBox!: ElementRef;

  chatText = '';
  typingUsers: string[] = [];

  private nearBottomThreshold = 120;

  typingTimeout: any;
  private typingSent = false;

  unreadCount = 0;

  openedMenuId: number | null = null;
  openedMessageId: number | null = null;

  showOnlyMyMessages = false;

  constructor(
    private ws: WebSocket,
    private router: Router
  ) {}

  ngOnInit() {

    this.ws.send({ action: 'load_chat' });

    this.ws.messages$.subscribe((msg: any) => {
      if (!msg) return;

      if (msg.action === 'init_chat') {
        this.messages = (msg.messages || []).map((m: any) => ({
          ...m,
          uid: String(m.uid)
        }));
        this.scrollToBottom();
      }

      if (msg.action === 'new_message') {
        const m = msg.message;
        if (!m) return;

        m.uid = String(m.uid);
        this.messages.push(m);
      }

      if (msg.action === 'online_users') {
        this.onlineUsers = msg.users;
      }

      if (msg.action === 'typing_start') {
        if (String(msg.uid) === this.uid) return;
        if (!this.typingUsers.includes(msg.name)) {
          this.typingUsers.push(msg.name);
        }
      }

      if (msg.action === 'typing_stop') {
        this.typingUsers = this.typingUsers.filter(u => u !== msg.name);
      }

      if (msg.action === 'message_deleted') {
        const m = this.messages.find(x => x.id === msg.message_id);
        if (m) m.deleted = 1;
      }

      if (msg.action === 'message_restored') {
        const m = this.messages.find(x => x.id === msg.message_id);
        if (m) m.deleted = 0;
      }
    });
  }

  sendMessage() {
    if (!this.chatText.trim()) return;

    if (this.typingSent) {
      this.typingSent = false;
      this.ws.send({ action: 'typing_stop' });
    }

    this.ws.send({
      action: 'send_message',
      text: this.chatText
    });

    this.chatText = '';
  }

  // CLICK MESSAGE → OPEN REACTION + MENU
  selectMessage(id: number, event: Event) {
    event.stopPropagation();

    if (this.openedMessageId === id) {
      this.openedMessageId = null;
      this.openedMenuId = null;
    } else {
      this.openedMessageId = id;
      this.openedMenuId = null;
    }
  }

  toggleMenu(id: number, event: Event) {
    event.stopPropagation();
    this.openedMenuId = this.openedMenuId === id ? null : id;
  }

  deleteMessage(id: number) {
    this.ws.send({
      action: 'delete_message',
      message_id: id
    });
  }

  restoreMessage(id: number) {
    this.ws.send({
      action: 'restore_message',
      message_id: id
    });
  }

  @HostListener('document:click')
  closeAll() {
    this.openedMessageId = null;
    this.openedMenuId = null;
  }

  scrollToBottom() {
    setTimeout(() => {
      if (!this.chatBox) return;
      this.chatBox.nativeElement.scrollTop =
        this.chatBox.nativeElement.scrollHeight;
    });
  }

  onTyping() {
    if (!this.typingSent) {
      this.typingSent = true;
      this.ws.send({ action: 'typing_start' });
    }

    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.typingSent = false;
      this.ws.send({ action: 'typing_stop' });
    }, 1000);
  }

  isFirstInGroup(index: number): boolean {
    if (index === 0) return true;

    const prev = this.messages[index - 1];
    const curr = this.messages[index];

    if (prev.uid !== curr.uid) return true;

    const prevTime = new Date(prev.timestamp).getTime();
    const currTime = new Date(curr.timestamp).getTime();

    return currTime - prevTime > 60000;
  }

  get filteredMessages() {
    return this.showOnlyMyMessages
      ? this.messages.filter(m => m.uid === this.uid)
      : this.messages;
  }

  back() {
    this.router.navigate(['/menu']);
  }

  ngOnDestroy() {
    clearTimeout(this.typingTimeout);

    if (this.typingSent) {
      this.ws.send({ action: 'typing_stop' });
    }
  }
}