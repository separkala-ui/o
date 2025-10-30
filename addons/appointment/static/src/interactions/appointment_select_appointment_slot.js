import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
const { DateTime } = luxon;

export class appointmentSlotSelect extends Interaction {
    static selector = ".o_appointment_info";
    dynamicContent = {
        "select[name='timezone']": {
            "t-on-change": this.onRefresh,
        },
        "select[id='selectAppointmentResource']": {
            "t-on-change": this.onRefresh,
        },
        "select[id='selectStaffUser']": {
            "t-on-change": this.onRefresh,
        },
        "select[id='resourceCapacity']": {
            "t-on-change": this.onRefresh,
        },
        ".o_js_calendar_navigate": {
            "t-on-click": this.onCalendarNavigate,
        },
        ".o_slot_button": {
            "t-on-click": this.onClickDaySlot,
        },
        ".o_slot_hours": {
            "t-on-click": this.onClickHoursSlot,
        },
        "button[name='submitSlotInfoSelected']": {
            "t-on-click": this.onClickConfirmSlot,
        },
        ".o_appointment_show_calendar": {
            "t-on-click": this.onClickShowCalendar,
        },
        "#next_available_slot": {
            "t-on-click": this.selectFirstAvailableMonth,
        },
        ".o_appointment_close_upcoming_appointment_alert": {
            "t-on-close.bs.alert": this.onClickCloseUpcomingAppointmentAlert,
        },
    };

    setup() {
        this.slotsListEl = this.el.querySelector("#slotsList");
        this.resourceSelectionEl = this.el.querySelector("#resourceSelection");
        this.firstEl = this.el.querySelector(".o_slot_button");
    }

    willStart() {
        (async () => {
            await this.initSlots();
            this.removeLoadingSpinner();
            this.firstEl?.click();
        })();
    }

    /**
     * Initializes variables and design
     * - slotsListEl: the block containing the availabilities
     * - resourceSelectionEl: resources or users selection for time_resource mode
     * - firstEl: the first day containing a slot
     */
    async initSlots() {
        await this.updateSlotAvailability();
    }

    /**
     * Finds the first day with an available slot, replaces the currently shown month and
     * click on the first date where a slot is available.
     */
    selectFirstAvailableMonth() {
        const firstMonthEl = this.firstEl.closest(".o_appointment_month");
        const currentMonthEl = document.querySelector(".o_appointment_month:not(.d-none)");
        currentMonthEl.classList.add("d-none");
        currentMonthEl
            .querySelectorAll("table")
            .forEach((table) => table.classList.remove("d-none"));
        currentMonthEl.querySelector(".o_appointment_no_slot_month_helper").remove();
        firstMonthEl.classList.remove("d-none");
        this.slotsListEl.replaceChildren();
        this.firstEl.click();
    }

    /**
     * Replaces the content of the calendar month with the no month helper.
     * Renders and appends its template to the element given as argument.
     * - monthEl: the month div to which we append the helper.
     */
    renderNoAvailabilityForMonth(monthEl) {
        const firstAvailabilityDate = this.firstEl.getAttribute("id");
        const staffUserEl = this.el.querySelector("#slots_form select[name='staff_user_id']");
        const staffUserNameSelectedOption = staffUserEl?.options[staffUserEl.selectedIndex];
        const staffUserName = staffUserNameSelectedOption?.textContent;
        monthEl.querySelectorAll("table").forEach((tableEl) => tableEl.classList.add("d-none"));

        this.renderAt("Appointment.appointment_info_no_slot_month", {
            firstAvailabilityDate: DateTime.fromISO(firstAvailabilityDate).toFormat("cccc dd MMMM yyyy"),
            staffUserName: staffUserName,
        }, monthEl);
    }

    _updateResourceCapacityOptions() {
        const capacitySelect = document.querySelector("select[name='resourceCapacity']");
        const resourceId = document.querySelector("#slots_form select[name='resource_id']")?.value;

        if (resourceId && capacitySelect?.value) {
            const max_resource_capacity = parseInt(
                document.querySelector("input[name='max_resource_capacity']")?.value || 0
            );
            const max_default_capacity = parseInt(
                document.querySelector("input[name='max_capacity']").value
            );
            const previousCapacitySelected = parseInt(capacitySelect.value);
            const max_capacity = max_resource_capacity || max_default_capacity;
            capacitySelect.replaceChildren();
            this.renderAt(
                "appointment.resources_capacity_options",
                {
                    asked_capacity: previousCapacitySelected <= max_capacity ? previousCapacitySelected : false,
                    max_capacity: max_capacity,
                },
                capacitySelect
            );
        }
    }

    /**
     * Checks whether any slot is available in the calendar.
     * If there isn't, adds an explicative message in the slot list, and hides the appointment details,
     * and make design width adjustment to have the helper message centered to the whole width.
     * In case, there is no slots based on capacity chosen then the details and calendar are not hidden.
     * If the appointment is missconfigured (missing user or missing availabilities),
     * display an explicative message. The calendar is then not displayed.
     * If there is an upcoming appointment booked, display a information before the the calendar
     *
     */
    async updateSlotAvailability() {
        if (!this.firstEl) { // No slot available
            if (!this.el.querySelector("select[name='resourceCapacity']")) {
                this.el
                    .querySelectorAll("#slots_availabilities")
                    .forEach((slotEl) => slotEl.replaceChildren());
                this.el.querySelector(".o_appointment_timezone_selection")?.classList.add("d-none");

                const staffUserEl = this.el.querySelector(
                    "#slots_form select[name='staff_user_id']"
                );
                const staffUserNameSelectedOption = staffUserEl?.options[staffUserEl.selectedIndex];
                const staffUserName = staffUserNameSelectedOption?.textContent;
                const hideSelectDropdown = !!this.el.querySelector(
                    "input[name='hide_select_dropdown']"
                ).value;
                this.el.querySelector(".o_appointment_no_slot_overall_helper").replaceChildren();
                this.renderAt("Appointment.appointment_info_no_slot", {
                    active: this.el.querySelector("input[name='active']").value,
                    appointmentsCount: parseInt(this.el.querySelector("#slotsList").dataset.appointmentsCount),
                    staffUserName: hideSelectDropdown ? staffUserName : false,
                }, this.el.querySelector(".o_appointment_no_slot_overall_helper"));

            } else {
                this.el.querySelector(".o_appointment_no_capacity")?.replaceChildren();
                this.renderAt("Appointment.appointment_info_no_capacity", {}, this.el.querySelector(".o_appointment_no_capacity"));
            }
        } else {
            this.el.querySelector(".o_appointment_timezone_selection")?.classList.remove("d-none");
            this.el.querySelector(".o_appointment_no_capacity")?.replaceChildren();
        }
        this.el.querySelector(".o_appointment_missing_configuration")?.classList.remove("d-none");
        // Check upcoming appointments
        const allAppointmentsToken = JSON.parse(localStorage.getItem("appointment.upcoming_events_access_token")) || [];
        const ignoreUpcomingEventUntil = localStorage.getItem("appointment.upcoming_events_ignore_until");
        if (!this.el.querySelector(".o_appointment_cancelled") &&
            !this.el.querySelector('.o_appointment_forced_staff_user_assigned') &&
            (!ignoreUpcomingEventUntil || deserializeDateTime(ignoreUpcomingEventUntil) < DateTime.utc()) &&
            (allAppointmentsToken.length !== 0 || user.userId !== false)
        ) {
            const upcomingAppointmentData = await this.waitFor(
                rpc("/appointment/get_upcoming_appointments", {
                    calendar_event_access_tokens: allAppointmentsToken,
                })
            );
            this.protectSyncAfterAsync(() => {
                if (upcomingAppointmentData) {
                    if (!localStorage.getItem('appointment.hide_upcoming_appointment_alert')){
                        const timezone = this.el.querySelector(".o_appointment_info_main").dataset.timezone;
                        const upcomingFormattedStart = deserializeDateTime(
                            upcomingAppointmentData.next_upcoming_appointment.start
                        ).setZone(timezone).toLocaleString(DateTime.DATETIME_MED_WITH_WEEKDAY);
                        
                        this.el.querySelector(".o_appointment_upcoming_appointment_alert").replaceChildren(); 
                        this.renderAt("Appointment.appointment_info_upcoming_appointment", {
                            appointmentTypeName: upcomingAppointmentData.next_upcoming_appointment.appointment_type_id[1],
                            appointmentStart: upcomingFormattedStart,
                            appointmentToken: upcomingAppointmentData.next_upcoming_appointment.access_token,
                            partnerId: upcomingAppointmentData.next_upcoming_appointment.appointment_booker_id[0],
                        }, this.el.querySelector(".o_appointment_upcoming_appointment_alert"));

                        if (user.userId === false) {
                            localStorage.setItem("appointment.upcoming_events_access_token", JSON.stringify(upcomingAppointmentData.valid_access_tokens));
                        }
                    } else {
                        localStorage.removeItem("appointment.upcoming_events_access_token");
                    }
                }
            })();
        }
    }

    /**
     * Navigate between the months available in the calendar displayed
     */
    onCalendarNavigate(ev) {
        const parentEl = this.el.querySelector(".o_appointment_month:not(.d-none)");
        let monthID = parseInt(parentEl.getAttribute("id").split("-")[1]);
        monthID += ev.currentTarget.getAttribute("id") === "nextCal" ? 1 : -1;
        parentEl.querySelectorAll("table").forEach((table) => table.classList.remove("d-none"));
        parentEl
            .querySelectorAll(".o_appointment_no_slot_month_helper")
            .forEach((element) => element.remove());
        parentEl.classList.add("d-none");
        const monthEl = this.el.querySelector(`div#month-${monthID}`);
        monthEl.classList.remove("d-none");
        this.el.querySelector(".active")?.classList.remove("active");
        this.slotsListEl.replaceChildren();
        this.resourceSelectionEl?.replaceChildren();

        if (this.firstEl) {
            // If there is at least one slot available, check if it is in the current month.
            if (!monthEl.querySelector(".o_day")) {
                this.renderNoAvailabilityForMonth(monthEl);
            }
        }
    }

    /**
     * Display the list of slots available for the date selected
     */
    onClickDaySlot(ev) {
        this.el
            .querySelectorAll(".o_slot_selected")
            .forEach((slot) => slot.classList.remove("o_slot_selected", "active"));
        ev.currentTarget.classList.add("o_slot_selected", "active");

        // Do not display slots until user has actively selected the capacity
        const resourceCapacityEl = this.el.querySelector("select[name='resourceCapacity']");
        const resourceCapacitySelectedOption =
            resourceCapacityEl?.options[resourceCapacityEl.selectedIndex];
        if (
            resourceCapacitySelectedOption &&
            resourceCapacitySelectedOption.dataset.placeholderOption
        ) {
            return;
        }
        const slotDate = ev.currentTarget.dataset.slotDate;
        const slots = JSON.parse(ev.currentTarget.dataset.availableSlots);
        const scheduleBasedOn = this.el.querySelector("input[name='schedule_based_on']").value;
        const selectAppointmentResourceEl = this.el.querySelector(
            "select[id='selectAppointmentResource']"
        );
        const resourceId =
            (selectAppointmentResourceEl && selectAppointmentResourceEl.value) ||
            this.el.querySelector("input[name='resource_selected_id']").value;
        const resourceCapacity = this.el.querySelector("select[name='resourceCapacity']")?.value;
        let commonUrlParams = new URLSearchParams(window.location.search);
        // If for instance the chosen slot is already taken, then an error is thrown and the
        // user is brought back to the calendar view. In order to keep the selected user, the
        // url will contain the previously selected staff_user_id (-> preselected in the dropdown
        // if there is one). If one changes the staff_user in the dropdown, we do not want the
        // previous one to interfere, hence we delete it. The one linked to the slot is used.
        // The same is true for duration and date_time used in form rendering.
        commonUrlParams.delete("staff_user_id");
        commonUrlParams.delete("resource_selected_id");
        commonUrlParams.delete("duration");
        commonUrlParams.delete("date_time");
        if (resourceCapacity) {
            commonUrlParams.set("asked_capacity", encodeURIComponent(resourceCapacity));
        }
        if (resourceId) {
            commonUrlParams.set("resource_selected_id", encodeURIComponent(resourceId));
        }

        this.slotsListEl.replaceChildren();
        this.renderAt("appointment.slots_list", {
            commonUrlParams: commonUrlParams,
            scheduleBasedOn: scheduleBasedOn,
            slotDate: DateTime.fromISO(slotDate).toFormat("cccc dd MMMM yyyy"),
            slots: slots,
            getAvailableResources: (slot) => {
                return scheduleBasedOn === "resources"
                    ? JSON.stringify(slot["available_resources"])
                    : false;
            },
            getAvailableUsers: (slot) => {
                return scheduleBasedOn === "users"
                    ? JSON.stringify(slot["available_staff_users"])
                    : false;
            },
        }, this.slotsListEl);
        this.resourceSelectionEl?.classList.add("d-none");
    }

    onClickHoursSlot(ev) {
        this.el
            .querySelector(".o_slot_hours.o_slot_hours_selected")
            ?.classList.remove("o_slot_hours_selected", "active");
        ev.currentTarget.classList.add("o_slot_hours_selected", "active");

        // If not in 'manual + date first' we directly go to the url for the slot
        // In the case we are in 'manual + date first', we don't want to open the link as we want to select a resource
        // before confirming the slot.
        const isAutoAssign = this.el.querySelector("input[name='is_auto_assign']").value;
        const isDateFirst = this.el.querySelector("input[name='is_date_first']").value;
        const scheduleBasedOn = this.el.querySelector("input[name='schedule_based_on']").value;
        if (isAutoAssign || !isDateFirst) {
            const appointmentTypeID = this.el.querySelector(
                "input[name='appointment_type_id']"
            ).value;
            const urlParameters = decodeURIComponent(
                this.el.querySelector(".o_slot_hours_selected").dataset.urlParameters
            );
            const url = new URL(
                `/appointment/${encodeURIComponent(appointmentTypeID)}/info?${urlParameters}`,
                location.origin);
            document.location = encodeURI(url.href);
            return;
        }

        const availableResources = ev.currentTarget.dataset.availableResources
            ? JSON.parse(ev.currentTarget.dataset.availableResources)
            : undefined;
        const availableStaffUsers = ev.currentTarget.dataset.availableStaffUsers
            ? JSON.parse(ev.currentTarget.dataset.availableStaffUsers)
            : undefined;
        const previousResourceIdSelected = this.el.querySelector(
            "select[name='resource_id']"
        )?.value;
        this.resourceSelectionEl.replaceChildren();
        this.renderAt("appointment.resources_list", {
            availableResources,
            availableStaffUsers,
            scheduleBasedOn,
        }, this.resourceSelectionEl);
        const availableEntity =
            scheduleBasedOn === "resources" ? availableResources : availableStaffUsers;
        const resourceIdEl = this.el.querySelector("select[name='resource_id']");
        if (availableEntity.length === 1) {
            resourceIdEl.setAttribute("disabled", true);
        }
        if (
            previousResourceIdSelected &&
            this.el.querySelector(
                `select[name='resource_id'] > option[value='${previousResourceIdSelected}']`
            )
        ) {
            resourceIdEl.value = previousResourceIdSelected;
        }
        this.resourceSelectionEl.classList.remove("d-none");
    }

    onClickConfirmSlot(ev) {
        const appointmentTypeID = this.el.querySelector("input[name='appointment_type_id']").value;
        const resourceId = parseInt(this.el.querySelector("select[name='resource_id']").value);
        const scheduleBasedOn = this.el.querySelector("input[name='schedule_based_on']").value;
        const urlParameters = decodeURIComponent(
            this.el.querySelector(".o_slot_hours_selected").dataset.urlParameters
        );
        const url = new URL(
            `/appointment/${encodeURIComponent(appointmentTypeID)}/info?${urlParameters}`,
            location.origin);
        const isAutoAssign = this.el.querySelector("input[name='is_auto_assign']").value;
        const isDateFirst = this.el.querySelector("input[name='is_date_first']").value;
        if (scheduleBasedOn === "resources") {
            const resourceCapacity =
                parseInt(this.el.querySelector("select[name='resourceCapacity']")?.value) || 1;
            const resourceSelected = this.el.querySelector(".o_resources_list").selectedOptions[0];
            let resourceIds = JSON.parse(url.searchParams.get("available_resource_ids"));
            if (
                isDateFirst && !isAutoAssign &&
                parseInt(resourceSelected.dataset.resourceCapacity) >= resourceCapacity
            ) {
                resourceIds = [resourceId];
            }
            url.searchParams.set("resource_selected_id", encodeURIComponent(resourceId));
            url.searchParams.set("available_resource_ids", JSON.stringify(resourceIds));
            url.searchParams.set("asked_capacity", encodeURIComponent(resourceCapacity));
        } else {
            url.searchParams.set("staff_user_id", encodeURIComponent(resourceId));
        }
        document.location = encodeURI(url.href);
    }

    onClickShowCalendar(ev) {  
        this.el.querySelector('.o_appointment_no_slot_overall_helper').textContent = "";
        this.el.querySelector('div.o_appointment_calendar').classList.remove('d-none');
        this.el.querySelector('div.o_appointment_calendar_form').classList.remove('d-none');
        localStorage.setItem("appointment.upcoming_events_ignore_until",
            serializeDateTime(DateTime.utc().plus({ days: 1 })));
    }

    /**
     * Refresh the slots info when the user modifies the timezone or the selected user.
     */
    async onRefresh(ev) {
        if (this.el.querySelector("#slots_availabilities")) {
            const daySlotSelected =
                this.el.querySelector(".o_slot_selected") &&
                this.el.querySelector(".o_slot_selected").dataset.slotDate;
            const appointmentTypeID = this.el.querySelector(
                "input[name='appointment_type_id']"
            ).value;
            const filterAppointmentTypeIds = this.el.querySelector(
                "input[name='filter_appointment_type_ids']"
            ).value;
            const filterUserIds = this.el.querySelector(
                "input[name='filter_staff_user_ids']"
            ).value;
            const inviteToken = this.el.querySelector("input[name='invite_token']").value;
            const previousMonthName = this.el.querySelector(
                ".o_appointment_month:not(.d-none) .o_appointment_month_name"
            )?.textContent;
            const staffUserID = this.el.querySelector(
                "#slots_form select[name='staff_user_id']"
            )?.value;
            const resourceID =
                this.el.querySelector("select[id='selectAppointmentResource']")?.value ||
                this.el.querySelector("input[name='resource_selected_id']")?.value;
            const filterResourceIds = this.el.querySelector(
                "input[name='filter_resource_ids']"
            ).value;
            const timezone = this.el.querySelector("select[name='timezone']")?.value;
            const resourceCapacity =
                (this.el.querySelector("select[name='resourceCapacity']") &&
                    parseInt(this.el.querySelector("select[name='resourceCapacity']").value)) ||
                1;
            this.el.querySelector(".o_appointment_no_slot_overall_helper").replaceChildren();
            this.slotsListEl.replaceChildren();
            this.el
                .querySelectorAll("#calendar, .o_appointment_timezone_selection")
                .forEach((el) => {
                    el.classList.add("o_appointment_disable_calendar");
                });
            this.resourceSelectionEl?.replaceChildren();
            const resourceCapacityEl = this.el.querySelector("select[name='resourceCapacity']");
            const resourceCapacitySelectedOption =
                resourceCapacityEl?.options[resourceCapacityEl.selectedIndex];
            if (
                daySlotSelected &&
                !(
                    resourceCapacitySelectedOption &&
                    resourceCapacitySelectedOption.dataset.placeholderOption
                )
            ) {
                this.el
                    .querySelector(".o_appointment_slot_list_loading")
                    .classList.remove("d-none");
            }
            const updatedAppointmentCalendarHtml = await rpc(
                `/appointment/${appointmentTypeID}/update_available_slots`,
                {
                    asked_capacity: resourceCapacity,
                    invite_token: inviteToken,
                    filter_appointment_type_ids: filterAppointmentTypeIds,
                    filter_staff_user_ids: filterUserIds,
                    filter_resource_ids: filterResourceIds,
                    month_before_update: previousMonthName,
                    resource_selected_id: resourceID,
                    staff_user_id: staffUserID,
                    timezone: timezone,
                }
            );
            if (updatedAppointmentCalendarHtml) {
                this.el.querySelector("#slots_availabilities").outerHTML = updatedAppointmentCalendarHtml;
                this.initSlots();
                this._updateResourceCapacityOptions();
                // If possible, we keep the current month, and display the helper if it has no availability.
                const displayedMonthEl = this.el.querySelector(".o_appointment_month:not(.d-none)");
                if (!!this.firstEl && !displayedMonthEl.querySelector(".o_day")) {
                    this.renderNoAvailabilityForMonth(displayedMonthEl);
                }
                this.removeLoadingSpinner();
                // Select previous selected date (in displayed month) if possible.
                const selectedDayEl = displayedMonthEl?.querySelector(`div[data-slot-date="${daySlotSelected}"]`);
                selectedDayEl && this.onClickDaySlot({ currentTarget: selectedDayEl });
            }
        }
    }

    /**
     * Remove the loading spinners when no longer useful
     */
    removeLoadingSpinner() {
        this.el.querySelector(".o_appointment_slots_loading")?.remove();
        this.el.querySelector(".o_appointment_slot_list_loading")?.classList.add("d-none");
        this.el.querySelector("#slots_availabilities")?.classList.remove("d-none");
        this.el.querySelectorAll("#calendar, .o_appointment_timezone_selection").forEach((el) => {
            el.classList.remove("o_appointment_disable_calendar");
        });
    }

    onClickCloseUpcomingAppointmentAlert() {
        localStorage.setItem('appointment.hide_upcoming_appointment_alert', true);
    }
}


registry
    .category("public.interactions")
    .add("appointment.appointment_select_appointment_slot", appointmentSlotSelect);

