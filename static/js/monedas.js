$(document).ready(function(){
	function ajax_pet () {
		$.ajax({
			url:"/monedas",
			data:$("form").serialize(),
			type:"POST",
			success:function(response){
				$(".error").remove();
				if (response.validation){
					location.href="/mi_cuenta";
				}
				else {
					if (response.error){
						$("#errors").append($("<li class='error'>"+response.error+'</li>'));
					}
				}
			},
			error:function(error){
				$(document).append($("<p>Error</p>"));
			}
		});
	}

	$("form").submit(function(event){
		event.preventDefault();
		ajax_pet();
	});

});
