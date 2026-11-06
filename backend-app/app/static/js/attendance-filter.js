/**
 * Cascading Attendance register filter.
 *
 * Department -> Trade -> Level -> Class -> Section. Every dropdown only lists
 * combinations that exist among the registered students the current user may
 * see, so an empty directory can never offer a class with no students.
 */
(() => {
    const form = document.querySelector("[data-attendance-filter]");
    if (!form) return;

    let placements = {};
    try {
        placements = JSON.parse(form.dataset.placement || "{}");
    } catch (error) {
        return;
    }

    const FIELDS = ["department", "trade", "level", "class_name", "class_section"];
    const LABELS = {
        department: "Department",
        trade: "Trade",
        level: "Level",
        class_name: "Class",
        class_section: "Class Section",
    };
    const select = name => form.querySelector(`select[name="${name}"]`);
    const selects = FIELDS.map(select);
    if (selects.some(item => !item)) return;
    const rows = Object.values(placements).filter(row => Array.isArray(row) && row.length === 5);

    function promptFor(index) {
        if (index === 0) return "All departments";
        const parent = selects[index - 1];
        if (!parent.value) return `Choose ${LABELS[FIELDS[index - 1]]} first...`;
        if (FIELDS[index] === "class_section") return "All sections";
        if (FIELDS[index] === "class_name") return "All classes";
        return `All ${LABELS[FIELDS[index]].toLowerCase()}s`;
    }

    function rebuild(index) {
        const target = selects[index];
        const chosen = target.value;
        const parents = selects.slice(0, index).map(item => item.value);
        const values = new Set();
        rows.forEach(row => {
            if (row.slice(0, index).every((value, position) => !parents[position] || value === parents[position])) {
                if (row[index]) values.add(row[index]);
            }
        });
        const ready = index === 0 || Boolean(parents[index - 1]);
        target.replaceChildren(new Option(
            ready ? promptFor(index) : `Choose ${LABELS[FIELDS[index - 1]]} first...`, ""));
        [...values].sort((a, b) => a.localeCompare(b)).forEach(value => {
            target.appendChild(new Option(
                FIELDS[index] === "class_section" && /^[a-z]+$/i.test(value) ? `${LABELS.class_section} ${value}` : value,
                value));
        });
        target.disabled = !ready || values.size === 0;
        if (ready && values.has(chosen)) target.value = chosen;
        return target.value;
    }

    function cascade(from) {
        for (let index = from + 1; index < selects.length; index += 1) {
            selects[index].value = "";
            if (!rebuild(index)) {
                // A cleared parent leaves deeper selectors unusable.
                for (let deeper = index + 1; deeper < selects.length; deeper += 1) {
                    selects[deeper].replaceChildren(new Option(
                        `Choose ${LABELS[FIELDS[deeper - 1]]} first...`, ""));
                    selects[deeper].disabled = true;
                }
                break;
            }
        }
    }

    function change(event) {
        cascade(FIELDS.indexOf(event.target.name));
        select("department").setCustomValidity(
            select("department").value ? "" : "Choose a department.");
    }

    selects.forEach((item, index) => {
        item.addEventListener("change", change);
        if (index === 0) {
            item.required = true;
            item.setCustomValidity(item.value ? "" : "Choose a department.");
        }
    });
})();
