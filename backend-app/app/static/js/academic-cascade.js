/**
 * Reusable cascading academic dropdown engine (framework-free).
 *
 * Turns any group of <select> elements marked with data-academic-* attributes
 * into relationally consistent cascading dropdowns backed by the database.
 *
 * Usage:
 *   <select data-academic="department" data-targets="trade,level,class"></select>
 *   <select data-academic="trade"    data-parent="department" data-targets="level,class"></select>
 *   <select data-academic="level"    data-parent="trade"></select>
 *   <select data-academic="class"    data-parent="level" data-id-field="class_id"></select>
 *   <select data-academic="module"   data-parent="level" data-require="trade,level"></select>
 *
 * Behaviour: loading indicators, empty-state messages, disabled states until
 * the parent is chosen, automatic resetting of dependents when a parent
 * changes, and preselection of existing values via data-initial attributes.
 */
(function () {
  "use strict";

  var API = "/api/academics/";
  var PLACEHOLDERS = {
    department: "Select a department first.",
    trade: "Select a department first.",
    level: "Select a trade or department first.",
    class: "Select a trade first.",
    module: "Select a class, trade, or department first."
  };
  var EMPTY_MESSAGES = {
    department: "No departments are configured.",
    trade: "No trades are available for this department.",
    level: "No levels are available for this selection.",
    "class": "No classes are assigned to this trade.",
    module: "No modules are available for this level."
  };

  function cascadeRoot(select) {
    var form = select.closest("form") || document;
    return form;
  }

  function findPeer(root, name) {
    return root.querySelector('select[data-academic="' + name + '"]');
  }

  function setOptions(select, items, placeholder, emptyMessage) {
    select.innerHTML = "";
    var ph = document.createElement("option");
    ph.value = "";
    ph.textContent = placeholder || PLACEHOLDERS[select.dataset.academic] || "Select...";
    select.appendChild(ph);
    items.forEach(function (item) {
      var option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      if (item.data) {
        Object.keys(item.data).forEach(function (key) {
          option.dataset[key] = item.data[key];
        });
      }
      select.appendChild(option);
    });
    select.disabled = items.length === 0;
    if (items.length === 0 && emptyMessage) {
      ph.textContent = emptyMessage;
    }
  }

  function showLoading(select) {
    select.innerHTML = "";
    var option = document.createElement("option");
    option.value = "";
    option.textContent = "Loading...";
    select.appendChild(option);
    select.disabled = true;
  }

  function resetDependents(select) {
    var targets = (select.dataset.targets || "").split(",").filter(Boolean);
    targets.forEach(function (name) {
      var dependent = findPeer(cascadeRoot(select), name.trim());
      if (!dependent) return;
      dependent.value = "";
      dependent.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  function initialValue(select) {
    return select.dataset.initial || "";
  }

  function applyInitial(select, items) {
    var initial = initialValue(select);
    if (!initial) return false;
    var match = items.some(function (item) { return String(item.value) === initial; });
    if (match) {
      select.value = initial;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    // Existing record does not match the current relational options;
    // keep the raw value but flag it for review.
    var option = document.createElement("option");
    option.value = initial;
    option.textContent = initial + " (review)";
    select.appendChild(option);
    select.value = initial;
    return true;
  }

  function loaders(kind, params, select) {
    var withSelect = function (promise, parser) {
      return promise.then(function (response) { return parser(response, select); });
    };
    switch (kind) {
      case "department":
        return withSelect(fetch(API + "departments"), parseList);
      case "trade":
        if (!params.departmentId) return Promise.resolve([]);
        return withSelect(fetch(API + "trades?department_id=" + params.departmentId), parseList);
      case "level":
        if (params.tradeId) {
          return fetch(API + "levels?trade_id=" + params.tradeId).then(parseLevels);
        }
        if (params.departmentId) {
          return fetch(API + "levels?department_id=" + params.departmentId).then(parseLevels);
        }
        return Promise.resolve([]);
      case "class":
        if (params.tradeId) {
          return withSelect(fetch(API + "classes?trade_id=" + params.tradeId +
            (params.level ? "&level=" + encodeURIComponent(params.level) : "")), parseClasses);
        }
        if (params.departmentId) {
          return withSelect(fetch(API + "classes?department_id=" + params.departmentId +
            (params.level ? "&level=" + encodeURIComponent(params.level) : "")), parseClasses);
        }
        return Promise.resolve([]);
      case "module":
        if (params.classId) {
          return withSelect(fetch(API + "modules?class_id=" + params.classId), parseModules);
        }
        if (params.tradeId) {
          return withSelect(fetch(API + "modules?trade_id=" + params.tradeId +
            (params.level ? "&level=" + encodeURIComponent(params.level) : "")), parseModules);
        }
        if (params.departmentId) {
          return withSelect(fetch(API + "modules?department_id=" + params.departmentId +
            (params.level ? "&level=" + encodeURIComponent(params.level) : "")), parseModules);
        }
        return Promise.resolve([]);
      default:
        return Promise.resolve([]);
    }
  }

  function valueField(select) {
    return select.dataset.valueField === "name" ? "name" : "id";
  }

  function parseList(response, select) {
    var field = valueField(select);
    return response.ok ? response.json().then(function (rows) {
      return rows.map(function (row) {
        var value = String(field === "name" ? row.name : row.id);
        var item = { value: value, label: row.name };
        if (field === "id") item.data = { name: row.name };
        return item;
      });
    }) : Promise.resolve([]);
  }

  function parseLevels(response) {
    return response.ok ? response.json().then(function (levels) {
      return levels.map(function (level) { return { value: level, label: level }; });
    }) : Promise.resolve([]);
  }

  function parseClasses(response, select) {
    var field = valueField(select);
    return response.ok ? response.json().then(function (rows) {
      return rows.map(function (row) {
        var value = String(field === "name" ? row.name : row.id);
        return { value: value, label: row.name,
                 data: field === "name" ? { level: row.level } : { level: row.level, classId: row.id } };
      });
    }) : Promise.resolve([]);
  }

  function parseModules(response, select) {
    var field = valueField(select);
    return response.ok ? response.json().then(function (rows) {
      return rows.map(function (row) {
        var label = (row.code ? row.code + " — " : "") + row.name +
          (row.level ? " (" + row.level + ")" : "");
        if (field === "name") {
          return { value: row.name, label: label, data: { level: row.level } };
        }
        return { value: String(row.id), label: label,
                 data: { moduleId: row.id, level: row.level } };
      });
    }) : Promise.resolve([]);
  }

  function parentValues(root, select) {
    var parentNames = (select.dataset.parents || select.dataset.parent || "")
      .split(",").filter(Boolean).map(function (name) { return name.trim(); });
    var values = {};
    parentNames.forEach(function (name) {
      var parent = findPeer(root, name);
      if (parent) values[name] = parent.value;
    });
    return values;
  }

  function refresh(select) {
    var root = cascadeRoot(select);
    var kind = select.dataset.academic;
    var parents = parentValues(root, select);
    var query = {
      departmentId: parents.department || "",
      tradeId: parents.trade || "",
      classId: parents["class"] || "",
      level: parents.level || ""
    };
    // A module or class needs at least one anchor to be meaningful.
    var anchored = kind === "department" ||
      Object.keys(query).some(function (key) { return key !== "level" && query[key]; });
    if (!anchored) {
      setOptions(select, [], PLACEHOLDERS[kind], EMPTY_MESSAGES[kind]);
      return;
    }
    showLoading(select);
    loaders(kind, query, select).then(function (items) {
      if (!items.length) {
        setOptions(select, [], PLACEHOLDERS[kind], EMPTY_MESSAGES[kind]);
        resetDependents(select);
        return;
      }
      setOptions(select, items, PLACEHOLDERS[kind]);
      if (select.dataset.initial) {
        applyInitial(select, items);
      }
    }).catch(function () {
      setOptions(select, [], "Could not load options. Try again.",
        "Could not load options. Refresh the page and try again.");
    });
  }

  function bind(select) {
    if (select.dataset.academicBound) return;
    select.dataset.academicBound = "true";
    var kind = select.dataset.academic;
    if (kind === "department") {
      // Departments are the root of every cascade: load immediately.
      refresh(select);
    }
    select.addEventListener("change", function () {
      resetDependents(select);
    });
    // Refresh own options whenever a parent changes.
    var root = cascadeRoot(select);
    var parentNames = (select.dataset.parents || select.dataset.parent || "")
      .split(",").filter(Boolean).map(function (name) { return name.trim(); });
    parentNames.forEach(function (name) {
      var parent = findPeer(root, name);
      if (parent) {
        parent.addEventListener("change", function () { refresh(select); });
      }
    });
  }

  function init(scope) {
    (scope || document).querySelectorAll("select[data-academic]").forEach(bind);
  }

  window.AcademicCascade = { init: init };
  document.addEventListener("DOMContentLoaded", function () { init(document); });
})();
