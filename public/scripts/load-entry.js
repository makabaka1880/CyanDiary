// Func to load entries

async function load() {
    // Extract date from URL
    const pathParts = window.location.pathname.split("/");
    const date = pathParts[pathParts.length - 1];

    // Fetching logic here
    try {
        // Fetch res
        const res = await fetch(`/req-entry?d=${date}`, {
            headers: {
                'x-api-key': localStorage.getItem('DIARY_VIEW_KEY')
            }
        });
        if (res.status === 403) {
            // If status is 403, handle it as a forbidden access err
            throw new Error('Forbidden: Invalid API Key or Access Denied.');
        }
        if (!res.ok) {
            throw new Error('response not okay'); // Handle req err
        }
        

        const { title, dateline, content } = await res.json(); // Extract body

        // Injection
        document.getElementById('headline-content').textContent = title;
        document.getElementById('dateline-content').textContent = dateline;
        document.getElementById('doc-content').innerHTML = content;

    } catch (err) {
        document.getElementById('headline-content').textContent = 'Error'
        document.getElementById('doc-content').textContent = err.message;
        if (err.message == 'Forbidden: Invalid API Key or Access Denied.') {
            document.getElementById('headline-content').textContent = 'Forbidden'
            document.getElementById('dateline-content').textContent = err.message;
            document.getElementById('doc-content').innerHTML = '不是哥们 我日记啊 我能让你看么';
        }
    }
}

load();