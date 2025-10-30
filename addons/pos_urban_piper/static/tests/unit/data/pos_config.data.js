import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

patch(PosConfig.prototype, {
    get_urban_piper_provider_states() {
        return {};
    },
});

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    module_pos_urban_piper: true,
}));
