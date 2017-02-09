$(document).ready(function(){
	function ajax_login () {
		$.ajax({
			url:"/login",
			data:$("#login-form").serialize(),
			type:"POST",
			success:function(response){
				$(".error").remove();
				if (response.validation){
					location.href="/mi_cuenta";
				}
				else {
					if (response.errors.account){
						for (var i = 0; i < response.errors.account.length; i++) {
							$("#errors-account").append($("<li class='error'>"+response.errors.account[i]+'</li>'));
						};
					}
					if (response.errors.password){
						for (var i = 0; i < response.errors.password.length; i++) {
							$("#errors-password").append($("<li class='error'>"+response.errors.password[i]+'</li>'));
						};
					}
				}
			},
			error:function(error){
				$(document).append($("<p>Error</p>"));
			}
		});
	}

	$("#login-form").submit(function(event){
		event.preventDefault();
		ajax_login();
	});

});
