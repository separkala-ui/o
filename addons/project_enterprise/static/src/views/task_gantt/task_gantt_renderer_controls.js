import { GanttRendererControls } from "@web_gantt/gantt_renderer_controls";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";


export class TaskGanttRendererControls extends GanttRendererControls {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.dependenciesActive = await user.hasGroup('project.group_project_task_dependencies');
        });
    }

    get displayRescheduleMethods() {
        return super.displayRescheduleMethods && this.dependenciesActive;
    }
}
