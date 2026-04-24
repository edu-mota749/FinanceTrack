(function () {
    function pad(value) {
        return String(value).padStart(2, "0");
    }

    function isValidDate(year, month, day) {
        const date = new Date(year, month - 1, day);
        return (
            date.getFullYear() === year &&
            date.getMonth() === month - 1 &&
            date.getDate() === day
        );
    }

    function toDisplayValue(isoValue, type) {
        if (!isoValue) {
            return "";
        }

        if (type === "date") {
            const parts = isoValue.split("-");
            if (parts.length === 3) {
                return `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
        }

        if (type === "month") {
            const parts = isoValue.split("-");
            if (parts.length >= 2) {
                return `${parts[1]}/${parts[0]}`;
            }
        }

        return isoValue;
    }

    function toIsoValue(rawValue, type) {
        const raw = String(rawValue || "").trim();
        if (!raw) {
            return "";
        }

        if (type === "date") {
            if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
                return raw;
            }

            const brDate = raw.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
            const compactDate = raw.match(/^(\d{2})(\d{2})(\d{4})$/);
            const parsed = brDate || compactDate;

            if (!parsed) {
                return null;
            }

            const day = Number(parsed[1]);
            const month = Number(parsed[2]);
            const year = Number(parsed[3]);

            if (!isValidDate(year, month, day)) {
                return null;
            }

            return `${year}-${pad(month)}-${pad(day)}`;
        }

        if (type === "month") {
            if (/^\d{4}-\d{2}$/.test(raw)) {
                return raw;
            }

            const brMonth = raw.match(/^(\d{1,2})[\/\-](\d{4})$/);
            const compactMonth = raw.match(/^(\d{2})(\d{4})$/);
            const parsed = brMonth || compactMonth;

            if (!parsed) {
                return null;
            }

            const month = Number(parsed[1]);
            const year = Number(parsed[2]);
            if (month < 1 || month > 12) {
                return null;
            }

            return `${year}-${pad(month)}`;
        }

        return null;
    }

    function createManualField(nativeInput) {
        if (nativeInput.dataset.manualDateReady === "true") {
            return;
        }

        const fieldType = nativeInput.type;
        nativeInput.dataset.manualDateReady = "true";
        nativeInput.dataset.nativeType = fieldType;

        const wrapper = document.createElement("div");
        wrapper.className = "manual-date-wrapper";

        const manualInput = document.createElement("input");
        manualInput.type = "text";
        manualInput.className = nativeInput.className;
        manualInput.classList.add("manual-date-text");
        manualInput.placeholder = fieldType === "month" ? "mm/aaaa" : "dd/mm/aaaa";
        manualInput.inputMode = "numeric";
        manualInput.autocomplete = "off";
        manualInput.value = toDisplayValue(nativeInput.value, fieldType);

        const pickerButton = document.createElement("button");
        pickerButton.type = "button";
        pickerButton.className = "manual-date-picker-btn";
        pickerButton.setAttribute("aria-label", "Abrir calendário");
        pickerButton.title = "Abrir calendário";
        pickerButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="3" y="5" width="18" height="16" rx="2"></rect><line x1="16" y1="3" x2="16" y2="7"></line><line x1="8" y1="3" x2="8" y2="7"></line><line x1="3" y1="11" x2="21" y2="11"></line></svg>';

        nativeInput.classList.add("manual-date-native");
        nativeInput.tabIndex = -1;

        const parent = nativeInput.parentNode;
        parent.insertBefore(wrapper, nativeInput);
        wrapper.appendChild(manualInput);
        wrapper.appendChild(pickerButton);
        wrapper.appendChild(nativeInput);

        function syncManualToNative(showError) {
            const iso = toIsoValue(manualInput.value, fieldType);

            if (iso === null) {
                nativeInput.setCustomValidity("Data inválida. Use o formato dd/mm/aaaa.");
                if (showError) {
                    nativeInput.reportValidity();
                    manualInput.focus();
                }
                return false;
            }

            nativeInput.setCustomValidity("");
            nativeInput.value = iso;
            manualInput.value = toDisplayValue(iso, fieldType);
            return true;
        }

        function syncNativeToManual() {
            manualInput.value = toDisplayValue(nativeInput.value, fieldType);
            nativeInput.setCustomValidity("");
        }

        pickerButton.addEventListener("click", function () {
            if (typeof nativeInput.showPicker === "function") {
                nativeInput.showPicker();
                return;
            }

            nativeInput.focus();
        });

        manualInput.addEventListener("blur", function () {
            syncManualToNative(false);
        });

        manualInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                syncManualToNative(true);
            }
        });

        nativeInput.addEventListener("change", syncNativeToManual);

        const form = nativeInput.closest("form");
        if (form) {
            form.addEventListener("submit", function (event) {
                const isValid = syncManualToNative(true);
                if (!isValid) {
                    event.preventDefault();
                }
            });
        }
    }

    function enableManualDateInputs() {
        const fields = document.querySelectorAll('input[type="date"], input[type="month"]');
        fields.forEach(createManualField);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", enableManualDateInputs);
    } else {
        enableManualDateInputs();
    }
})();
