import { useService } from "@web/core/utils/hooks";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

/**
 * The SidebarRow component is responsible of displaying an article (and its
 * children recursively) in a section of the sidebar, and modifying the record
 * of the article.
 */
export class KnowledgeSidebarRow extends Component {
    static props = {
        article: Object,
        unfolded: Boolean,
        unfoldedIds: Set,
        record: Object,
    };
    static template = "knowledge.SidebarRow";
    static components = {
        KnowledgeSidebarRow
    };

    setup() {
        super.setup();
        this.orm = useService("orm");

        this.state = useState({
            unfolded: false,
        });

        onWillUpdateProps(nextProps => {
            // Remove the loading spinner when the article is rendered as
            // being unfolded
            if (this.state.loading && nextProps.unfolded === true) {
                this.state.loading = false;
            }
        });
    }

    get hasChildren() {
        return this.props.article.has_article_children;
    }

    get isActive() {
        return this.props.record.resId === this.props.article.id;
    }

    get isLocked() {
        return this.props.article.is_locked;
    }

    get isReadonly() {
        return !this.props.article.user_can_write;
    }

    /**
     * Create a new child article for the row's article.
     */
    createChild() {
        this.env.createArticle(this.props.article.category, this.props.article.id);
    }

    /**
     * (Un)fold the row
     */
    onCaretClick() {
        if (this.props.unfolded) {
            this.env.fold(this.props.article.id);
        } else if (!this.state.loading) {
            this.state.loading = true;
            // If there are a lot of articles, make sure the rendering caused
            // by the state change and the one cause by the prop update are not
            // done at once, because otherwise the loader will not be shown.
            // If there are not too much articles, the renderings can be done
            // at once so that there is no flickering.
            if (this.props.article.child_ids.length > 500) {
                setTimeout(() => this.env.unfold(this.props.article.id), 0);
            } else {
                this.env.unfold(this.props.article.id);
            }
        }
    }

    /**
     * Open the row's article
     */
    onNameClick() {
        this.env.openArticle(this.props.article.id);
    }
}
