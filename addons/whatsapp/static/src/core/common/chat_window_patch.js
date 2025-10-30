import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    get showImStatus() {
        return (
            super.showImStatus ||
            (this.thread?.channel_type === "whatsapp" && this.thread.correspondent)
        );
    },
});
