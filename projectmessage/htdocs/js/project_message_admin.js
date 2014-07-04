$( document ).ready(function() {
  $("#project-message-form").validate({errorClass: "ui-state-error"});
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

});
