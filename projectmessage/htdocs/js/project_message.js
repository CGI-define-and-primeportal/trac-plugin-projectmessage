$( document ).ready(function() {

  // Listen to full screen agreement
  $("#project-message-agreement-btn").click(function(e) {
    e.preventDefault();
    $.ajax({
      type:"POST",
      data: $("#project-message-form").serialize(),
      url: window.tracBaseUrl + "ajax/projectmessage",
      success: function() {
        window.location.replace(tracBaseUrl);
      }
    });
  });

  // Listen to alert agreement (via closing the alert box)
  $("button.close", ".project-message").click(function(e){
    e.preventDefault();
    $.ajax({
      type:"POST",
      data: $(this).parent().next("form").serialize(),
      url: window.tracBaseUrl + "ajax/projectmessage"
    });
  });

});
