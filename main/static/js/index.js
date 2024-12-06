function check_username(element) {
    $("#username-success").hide();
    $("#username-error").hide();

    var username = $(element).val(); // Получаем значение из поля ввода
    if (username == "") {
        return; // Если поле пустое, выходим из функции
    }

    $.ajax({
        url: $(element).attr("data-url"), // URL для проверки логина
        data: {
            "csrfmiddlewaretoken": $("input[name='csrfmiddlewaretoken']").val(), // Извлекаем CSRF-токен
            "username": username // Отправляем имя пользователя
        },
        method: "POST",
        dataType: "json",
        success: function(returned_data) {
            if (returned_data.exists) { // Проверяем, существует ли логин
                $('#username-error').show(); // Показываем сообщение об ошибке
                $('#username-success').hide(); // Скрываем сообщение об успехе
            } else {
                $('#username-success').show(); // Показываем сообщение об успехе
                $('#username-error').hide(); // Скрываем сообщение об ошибке
            }
        },
        error: function(xhr, status, error) {
            console.error('Ошибка AJAX:', status, error); // Логируем ошибку в консоль
        }
    });
}