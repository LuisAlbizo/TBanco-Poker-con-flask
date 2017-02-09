$(document).ready(function(){
	var socket = io.connect('http://127.0.0.1:8080/chat');

	socket.on('connect',function(){
		socket.emit("mensaje","he entrado al chat.");
	});

	socket.on('mensaje',function(msg){
		$('#mensajes').append($("<li class='mensaje-recv'>"+msg+"</li>"));
	});

	$("#send").on("click",function(){
		socket.emit('mensaje',$("#mensaje").val());
		$("#mensaje").val("");
	});

});
