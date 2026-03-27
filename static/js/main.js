(() => {
	const root = document.documentElement;
	const toggle = document.getElementById("theme-toggle");
	if (!toggle) {
		return;
	}

	const icon = toggle.querySelector(".theme-toggle-icon");
	const label = toggle.querySelector(".theme-toggle-label");

	function updateToggleUI(theme) {
		const isDark = theme === "dark";
		toggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
		if (icon) {
			icon.textContent = isDark ? "☀" : "☾";
		}
		if (label) {
			label.textContent = isDark ? "Day" : "Night";
		}
	}

	const initialTheme = root.getAttribute("data-theme") || "light";
	updateToggleUI(initialTheme);

	toggle.addEventListener("click", () => {
		const current = root.getAttribute("data-theme") || "light";
		const nextTheme = current === "dark" ? "light" : "dark";
		root.setAttribute("data-theme", nextTheme);
		localStorage.setItem("spendly-theme", nextTheme);
		updateToggleUI(nextTheme);
	});
})();
