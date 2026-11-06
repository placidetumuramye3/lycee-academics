(() => {
    const container = document.getElementById('teacher-assignments');
    const template = document.getElementById('teacher-assignment-template');
    if (!container || !template) return;

    function setup(row) {
        const trade = row.querySelector('.assignment-trade');
        const level = row.querySelector('.assignment-level');
        const klass = row.querySelector('.assignment-class');
        const subject = row.querySelector('.assignment-subject');
        const levels = [...level.querySelectorAll('option[data-trade]')];
        const classes = [...klass.querySelectorAll('option[data-trade]')];
        const modules = [...subject.querySelectorAll('option[data-trade]')];

        function reset(select, prompt, options, enabled) {
            select.replaceChildren(new Option(prompt, ''));
            options.forEach(option => select.appendChild(option.cloneNode(true)));
            select.disabled = !enabled;
            // The shared filterable-select enhancement listens for `change` to
            // refresh its visible options, so announce every catalogue update.
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function updateSubjects() {
            const selectedClass = klass.selectedOptions[0];
            const ready = Boolean(klass.value && selectedClass.dataset.trade === trade.value &&
                selectedClass.dataset.level === level.value);
            const matching = ready ? modules.filter(option =>
                option.dataset.trade === trade.value && option.dataset.level === level.value) : [];
            reset(subject, !ready ? 'Choose class first...' : matching.length ?
                'Choose module / subject...' : 'No modules available for this class', matching, ready);
        }

        function updateClasses() {
            const ready = Boolean(trade.value && level.value);
            reset(klass, ready ? 'Choose class...' : 'Choose level first...',
                ready ? classes.filter(option => option.dataset.trade === trade.value &&
                    option.dataset.level === level.value) : [], ready);
            updateSubjects();
        }

        function updateLevels() {
            reset(level, trade.value ? 'Choose level...' : 'Choose trade first...',
                levels.filter(option => option.dataset.trade === trade.value), Boolean(trade.value));
            updateClasses();
        }

        trade.addEventListener('change', updateLevels);
        level.addEventListener('change', updateClasses);
        klass.addEventListener('change', updateSubjects);
        row.querySelector('.remove-assignment').addEventListener('click', () => {
            if (container.children.length > 1) row.remove();
        });
        updateLevels();
    }

    container.querySelectorAll('.teacher-assignment').forEach(setup);
    document.getElementById('add-teacher-assignment').addEventListener('click', () => {
        const fragment = template.content.cloneNode(true);
        const row = fragment.querySelector('.teacher-assignment');
        container.appendChild(fragment);
        setup(row);
    });
})();
