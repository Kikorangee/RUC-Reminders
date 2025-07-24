// Geotab Add-In loader for RUC Dashboard

window.geotab = window.geotab || {};
window.geotab.addin = window.geotab.addin || {};

window.geotab.addin.rucDashboard = function(api, state) {
  return {
    initialize: function(api, state, callback) {
      window.api = api;
      callback();
    },
    focus: function() {},
    blur: function() {}
  };
};
