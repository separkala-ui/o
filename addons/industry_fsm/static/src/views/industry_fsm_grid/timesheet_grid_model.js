import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { TimesheetGridModel } from "@timesheet_grid/views/timesheet_grid/timesheet_grid_model";

patch(TimesheetGridModel.prototype, {
    /**
     * @override
     */
    _getPreviousWeekTimesheetDomain() {
        return Domain.and([super._getPreviousWeekTimesheetDomain(), [["project_id.is_fsm", "=", false]]]);
    },

    /**
     * @override
     */
    _getFavoriteTaskDomain(searchParams) {
        return Domain.and([super._getFavoriteTaskDomain(searchParams), [["is_fsm", "=", false]]]);
    },
});
