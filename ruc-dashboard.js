// Geotab Add-In loader for RUC Dashboard
// This exposes the Geotab API object to your React app via window.api

window.geotab = window.geotab || {};
window.geotab.addin = window.geotab.addin || {};

window.geotab.addin.rucDashboard = function(api, state) {
  return {
    initialize: function(api, state, callback) {
      // Make Geotab API accessible to the React frontend
      window.api = api;
      callback();
    },
    focus: function() {
      // Optional: code to run when Add-In is focused
    },
    blur: function() {
      // Optional: code to run when Add-In is blurred
    }
  };
};