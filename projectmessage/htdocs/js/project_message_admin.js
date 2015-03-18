$( document ).ready(function() {
  $("#project-message-form").validate({
    errorClass: "ui-state-error",
    errorPlacement: function(error, element) {
      var trigger = element.next('.ui-datepicker-trigger');
      error.insertAfter(trigger.length > 0 ? trigger : element);
    }
  });

  $("#mode-select, #scope-select, #group-select").select2();

 $('#start_date,#end_date').datepicker({
    minDate:0,
    onSelect: function(dateText, inst){
      var date1 = $('#start_date').datepicker('getDate'),
          date2 = $('#end_date').datepicker('getDate');

      if(date1) {
        var dt = new Date(date1),
            start = new Date(dt.getFullYear(), dt.getMonth(), dt.getDate()+1);
        $('#end_date').datepicker('option','minDate',start);
      }
      else {
        $(this).datepicker('option','minDate',0);
      }
      $(this).attr('readOnly','true');
    },
  });

  $('.fa fa-question-circle').on('click', function() {
    $("#" + this.id.replace('help', 'dialog')).dialog({
      title: 'Project Message Help',
      width: 400,
      modal: true,
      buttons: {
        'Close': function() {
          $(this).dialog('close');
        }
      }
    });
  });

});
