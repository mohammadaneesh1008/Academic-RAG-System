const pdfFile = document.getElementById("pdfFile");
const fileName = document.getElementById("fileName");
const uploadBtn = document.getElementById("uploadBtn");

const question = document.getElementById("question");
const askBtn = document.getElementById("askBtn");

const chatBox = document.getElementById("chatBox");
const welcome = document.getElementById("welcome");


// ==============================
// PDF FILE SELECTION
// ==============================

pdfFile.addEventListener("change", () => {

    if (pdfFile.files.length > 0) {

        fileName.textContent =
            pdfFile.files[0].name;

    } else {

        fileName.textContent =
            "No file selected";
    }

});


// ==============================
// UPLOAD PDF
// ==============================

uploadBtn.addEventListener("click", async () => {

    if (pdfFile.files.length === 0) {

        alert("Please select a PDF first.");

        return;
    }


    const formData = new FormData();

    formData.append(
        "file",
        pdfFile.files[0]
    );


    uploadBtn.disabled = true;

    uploadBtn.textContent =
        "Processing...";


    try {

        const response = await fetch(
            "/upload",
            {
                method: "POST",
                body: formData
            }
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Upload failed"
            );

        }


        alert(
            data.message ||
            "PDF processed successfully!"
        );


    } catch (error) {

        alert(
            "Error: " + error.message
        );

    }


    uploadBtn.disabled = false;

    uploadBtn.textContent =
        "Upload & Process";

});


// ==============================
// ASK QUESTION
// ==============================

askBtn.addEventListener(
    "click",
    askQuestion
);


question.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            askQuestion();

        }

    }
);


// ==============================
// ASK FUNCTION
// ==============================

async function askQuestion() {

    const q =
        question.value.trim();


    if (!q) {
        return;
    }


    // Remove welcome screen
    if (welcome) {

        welcome.remove();

    }


    // Show user question

    addUserMessage(q);


    question.value = "";

    askBtn.disabled = true;


    // Loading message

    const loading = document.createElement("div");

    loading.className = "message";

    loading.innerHTML = `

        <div class="message-icon bot-icon">
            🤖
        </div>

        <div class="message-content">

            <div class="message-role">
                Academic RAG
            </div>

            <div class="message-text">

                <div class="loading">

                    <div class="spinner"></div>

                    Searching documents and generating answer...

                </div>

            </div>

        </div>

    `;

    chatBox.appendChild(loading);

    scrollToBottom();


    try {

        const response = await fetch(
            "/ask",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    question: q
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to get answer"
            );

        }


        // Remove loading

        loading.remove();


        // Show answer

        addAssistantMessage(
            data.answer,
            data.sources || []
        );


    } catch (error) {

        loading.remove();


        addAssistantMessage(
            "Sorry, something went wrong: " +
            error.message,
            []
        );

    }


    askBtn.disabled = false;

    question.focus();

}


// ==============================
// USER MESSAGE
// ==============================

function addUserMessage(text) {

    const message =
        document.createElement("div");

    message.className =
        "message";


    message.innerHTML = `

        <div class="message-icon user-icon">
            👤
        </div>

        <div class="message-content">

            <div class="message-role">
                You
            </div>

            <div class="message-text">
                ${escapeHtml(text)}
            </div>

        </div>

    `;


    chatBox.appendChild(message);

    scrollToBottom();

}


// ==============================
// ASSISTANT MESSAGE
// ==============================

function addAssistantMessage(
    answer,
    sources
) {

    const message =
        document.createElement("div");

    message.className =
        "message";


    let sourcesHTML = "";


    if (sources.length > 0) {

        sourcesHTML = `

            <details class="sources">

                <summary>
                    📄 Retrieved Sources
                </summary>

                ${sources.map(
                    (source, index) => {

                        const name =
                            source.source ||
                            "Unknown document";

                        const page =
                            source.page ||
                            "?";

                        return `

                            <div class="source">

                                <div class="source-title">
                                    ${index + 1}.
                                    ${escapeHtml(name)}
                                </div>

                                <div class="source-page">
                                    Page ${page}
                                </div>

                            </div>

                        `;

                    }
                ).join("")}

            </details>

        `;

    }


    message.innerHTML = `

        <div class="message-icon bot-icon">
            🤖
        </div>

        <div class="message-content">

            <div class="message-role">
                Academic RAG
            </div>

            <div class="message-text">

                ${formatAnswer(answer)}

                ${sourcesHTML}

            </div>

        </div>

    `;


    chatBox.appendChild(message);

    scrollToBottom();

}


// ==============================
// FORMAT ANSWER
// ==============================

function formatAnswer(text) {

    if (!text) {
        return "";
    }


    return escapeHtml(text)
        .replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        )
        .replace(
            /\n/g,
            "<br>"
        );

}


// ==============================
// SECURITY
// ==============================

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

}


// ==============================
// SCROLL
// ==============================

function scrollToBottom() {

    chatBox.scrollTo({
        top: chatBox.scrollHeight,
        behavior: "smooth"
    });

}