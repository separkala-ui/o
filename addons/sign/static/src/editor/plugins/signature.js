import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { withSequence } from "@html_editor/utils/resource";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { SignNameAndSignatureDialog } from "@sign/dialogs/dialogs";

export class SignaturePlugin extends Plugin {
    static id = "signature";
    static dependencies = ["dom", "history"];
    resources = {
        user_commands: [
            {
                id: "insertSignature",
                title: _t("Signature"),
                description: _t("Insert your signature"),
                icon: "fa-pencil-square-o",
                run: this.insertSignature.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_categories: withSequence(100, { id: "basic_block", name: _t("Basic Bloc") }),
        powerbox_items: [
            {
                categoryId: "basic_block",
                commandId: "insertSignature",
            },
        ],
    };

    insertSignature() {
        const signature = { name: user.name };
        const close = this.services.dialog.add(SignNameAndSignatureDialog, {
            signature,
            activeFrame: true,
            frame: {},
            hash: "hash",
            displaySignatureRatio: 3,
            onConfirm: () => {
                const img = document.createElement("img");
                img.classList.add("img", "img-fluid", "o_we_custom_image");
                img.style = "width: 50%";
                img.src = signature.getSignatureImage();
                this.dependencies.dom.insert(img);
                this.dependencies.history.addStep();
                close();
            },
        });
    }
}
