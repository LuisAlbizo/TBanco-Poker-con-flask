$(document).ready(function(){
	var socket = io.connect('http://127.0.0.1:8080/chat');

	socket.on('connect',function(){
		socket.emit("mensajeClient","he entrado al chat.");
	});

	socket.on('mensajeServer',function(msg){
		$('#mensajes').append($("<li class='mensaje-recv'><span class='time'>["+msg.time+"]</span>"+"<span class='user' style='color:"+msg.color+";'>"+msg.user+"</span>> <span class='msg'>"+msg.msg+"</span></li>"));
	});

	$("#send").on("click",function(){
		if ($("#mensaje").val())
			socket.emit('mensajeClient',$("#mensaje").val());
		$("#mensaje").val("");
	});

});
