$(document).ready(function(){
	function ajax_register () {
		$.ajax({
			url:"/register",
			data:$("#register-form").serialize(),
			type:"POST",
			success:function(response){
				$(".error").remove();
				if (response.validation){
					location.href="/login";
				}
				else {
					if (response.errors.password){
						for (var i = 0; i < response.errors.password.length; i++) {
							$("#errors-password").append($("<li class='error'>"+response.errors.password[i]+'</li>'));
						};
					}
					if (response.errors.confirm){
						for (var i = 0; i < response.errors.confirm.length; i++) {
							$("#errors-confirm").append($("<li class='error'>"+response.errors.confirm[i]+'</li>'));
						};
					}
				}
			},
			error:function(error){
			}
		});
	}

	$("#register-form").submit(function(event){
		event.preventDefault();
		ajax_register();
	});

});
