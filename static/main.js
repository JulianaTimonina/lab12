// static/main.js
function getToken() {
    const token = localStorage.getItem('access_token');
    // Если значение отсутствует или буквально строка "null"/"undefined" — считаем токен невалидным
    if (!token || token === 'null' || token === 'undefined') {
        return null;
    }
    return token;
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}

async function fetchWithAuth(url, method = 'GET', body = null) {
    const token = getToken();
	console.log('Token used:', token);
    if (!token) {
        logout();
        throw new Error('No token');
    }

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
    const options = { method, headers };
    if (body) {
        options.body = JSON.stringify(body);
    }

    let response;
    try {
        response = await fetch(url, options);
    } catch (err) {
        logout();
        throw err;
    }

    // Любой ответ, означающий проблемы с авторизацией/токеном → выход
    if (response.status === 401 || response.status === 422) {
        logout();
        throw new Error('Token invalid');
    }

    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.msg || `Ошибка ${response.status}`);
    }

    return response.json();
}