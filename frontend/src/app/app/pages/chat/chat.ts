import { Component, ElementRef, HostListener, ViewChild, OnInit, OnDestroy } from '@angular/core';
import { WebSocket } from '../../services/web-socket';
import { Router } from '@angular/router';
import { Title } from '@angular/platform-browser';

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
  @ViewChild('chatBox') chatBox!: ElementRef;
  onlineUsers:any[] = [];
  chatText = '';
  private nearBottomThreshold = 120;
  typingUsers: string[] = [];
  typingTimeout: any;
  private typingSent = false;
  unreadCount = 0;
  openedMenuId: number | null = null;
  showOnlyMyMessages = false;

  constructor(private ws: WebSocket, private router: Router,private titleService: Title) { }

  ngOnInit() {
    // this.titleService.setTitle('Daily Chat');

    this.ws.send({
      action: 'load_chat'
    });

    this.ws.messages$.subscribe((msg: any) => {
      if (!msg) return;

      if (msg.action === 'init_chat') {
      const map = new Map();

        for (const m of msg.messages || []) {
        m.uid = String(m.uid);
        map.set(m.id, m);
      }

      this.messages = Array.from(map.values());
      this.scrollToBottom();
    }

      if (msg.action === 'new_message') {
        if (msg.message) {
          msg.message.uid = String(msg.message.uid); 
        }        
        const shouldScroll = this.isNearBottom();

        this.messages.push(msg.message);
        if (shouldScroll) {
          this.scrollToBottom();
        }

      }
      if(msg.action === 'online_users') {
        this.onlineUsers = msg.users;
      }

      if (msg.action === 'typing_start') {
        if (String(msg.uid) === String(this.uid)) return;
        if (!this.typingUsers.includes(msg.name)) {
          this.typingUsers.push(msg.name);
        }
      }

      if (msg.action === 'typing_stop') {
        this.typingUsers =
          this.typingUsers.filter(
            u => u !== msg.name
          );
      }

      if (msg.action === 'message_deleted') {
        const m = this.messages.find(x => x.id === msg.message_id);
        if (m) m.deleted = 1;
      }

      if (msg.action === 'message_restored') {
        const m = this.messages.find(x => x.id === msg.message_id);
        if (m) m.deleted = 0;
      }

      if (msg.action === 'mention') {
        if (msg.to === this.name) {
          this.unreadCount++;
        }
      }
      
      
    });

  }

  // clearUnread() {
  //   this.unreadCount = 0;
  //   this.titleService.setTitle('Daily Chat');
  // }

  sendMessage() {
      if (!this.chatText.trim()) return;
      if (this.typingSent) {
        this.typingSent = false;
        this.ws.send({
          action: 'typing_stop'
        });
      }
      this.ws.send({
        action: 'send_message',
        text: this.chatText
      });

      this.chatText = '';
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

  scrollToBottom() {
    setTimeout(() => {
      if (!this.chatBox) return;

      this.chatBox.nativeElement.scrollTop = this.chatBox.nativeElement.scrollHeight;
    });
  }

  isNearBottom(): boolean {
    if (!this.chatBox) return true;

    const el = this.chatBox.nativeElement;
    const position = el.scrollTop + el.clientHeight;
    const height = el.scrollHeight;

    return position > height - this.nearBottomThreshold;
  }
  onTyping() {

    if (!this.typingSent) {
      this.typingSent = true;
      this.ws.send({
        action: 'typing_start'
      });
    }

    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.typingSent = false;
      this.ws.send({
        action: 'typing_stop'
      });
    }, 1000);

  }

  isFirstInGroup(index: number): boolean {
    if (index === 0) return true;

    const prev = this.messages[index - 1];
    const curr = this.messages[index];

    // Different user or more than 60 seconds gap
    if (prev.uid !== curr.uid) return true;

    const prevTime = new Date(prev.timestamp).getTime();
    const currTime = new Date(curr.timestamp).getTime();
    return (currTime - prevTime) > 60000;
  }

  toggleMenu(id: number, event: Event) {

    event.stopPropagation();

    if (this.openedMenuId === id) {
      this.openedMenuId = null;
    } else {
      this.openedMenuId = id;
    }
  }
  @HostListener('document:click')
  closeMenu() {
    this.openedMenuId = null;
  }
  highlightMentions(text: string) {
    return text.replace(/@(\w+)/g, '<b>@$1</b>');
  }
  my_messages() { 
    this.showOnlyMyMessages = !this.showOnlyMyMessages;
  }

  get filteredMessages() {
    return this.showOnlyMyMessages
      ? this.messages.filter(m => m.uid === this.uid)
      : this.messages;
  }

  back() { this.router.navigate(['/menu']); }

  ngOnDestroy() {
    clearTimeout(this.typingTimeout);
    // this.titleService.setTitle('ClickGame');
    if (this.typingSent) {
      this.ws.send({
        action: 'typing_stop'
      });
    }
  }
}