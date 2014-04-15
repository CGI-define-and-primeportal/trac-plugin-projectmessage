$( document ).ready(function() {
  $("#project-message-form").validate({errorClass: "ui-state-error"});
  $("#mode-select, #scope-select, #group-select").select2();
});