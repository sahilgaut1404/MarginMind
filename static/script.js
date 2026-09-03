/* =========================================================
   HELPER
========================================================= */

async function getJSON(url, options = {}) {

    const response = await fetch(url, options);

    let data;

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        throw new Error(
            data.detail || `Request failed: ${response.status}`
        );
    }

    return data;
}


/* =========================================================
   DASHBOARD SUMMARY
========================================================= */

async function loadDashboardSummary() {

    const revenueElement = document.getElementById("revenue");
    const ordersElement = document.getElementById("orders");
    const unitsElement = document.getElementById("units");

    // Not dashboard page
    if (!revenueElement && !ordersElement && !unitsElement) {
        return;
    }

    try {

        const data = await getJSON("/dashboard summary");

        if (revenueElement) {
            revenueElement.innerText =
                "₹" + (data.total_revenue / 100).toFixed(2);
        }

        if (ordersElement) {
            ordersElement.innerText =
                data.total_orders;
        }

        if (unitsElement) {
            unitsElement.innerText =
                data.units_sold;
        }

    } catch (error) {

        console.error("Dashboard error:", error);

    }
}


/* =========================================================
   PRODUCTS
========================================================= */

let products = [];


async function loadProducts() {

    const productSelect =
        document.getElementById("product");

    if (!productSelect) {
        return;
    }

    try {

        products = await getJSON("/product");

        productSelect.innerHTML =
            '<option value="">Select a product</option>';

        products.forEach(product => {

            const option =
                document.createElement("option");

            option.value = product.id;

            option.textContent =
                `${product.name} - ₹${(
                    product.price / 100
                ).toFixed(2)}`;

            productSelect.appendChild(option);
        });

    } catch (error) {

        console.error("Product loading error:", error);

        productSelect.innerHTML =
            '<option value="">Unable to load products</option>';
    }
}


/* =========================================================
   CHECKOUT
========================================================= */

function initializeCheckout() {

    const productSelect =
        document.getElementById("product");

    const quantityInput =
        document.getElementById("quantity");

    const totalElement =
        document.getElementById("total");

    const payButton =
        document.getElementById("payButton");

    // Not dashboard / checkout page
    if (
        !productSelect ||
        !quantityInput ||
        !totalElement ||
        !payButton
    ) {
        return;
    }


    function calculateTotal() {

        const productId =
            productSelect.value;

        const quantity =
            Number(quantityInput.value);

        if (
            productId === "" ||
            !Number.isInteger(quantity) ||
            quantity <= 0
        ) {

            totalElement.innerText = "₹0.00";
            return;
        }

        const product =
            products.find(
                product => product.id == productId
            );

        if (!product) {

            totalElement.innerText = "₹0.00";
            return;
        }

        const amount =
            product.price * quantity;

        totalElement.innerText =
            "₹" + (amount / 100).toFixed(2);
    }


    productSelect.addEventListener(
        "change",
        calculateTotal
    );

    quantityInput.addEventListener(
        "input",
        calculateTotal
    );


    payButton.addEventListener(
        "click",
        async function () {

            try {

                const productId =
                    productSelect.value;

                const quantity =
                    Number(quantityInput.value);


                const product =
                    products.find(
                        product => product.id == productId
                    );


                if (!product) {

                    alert(
                        "Please select a product."
                    );

                    return;
                }


                if (
                    !Number.isInteger(quantity) ||
                    quantity <= 0
                ) {

                    alert(
                        "Please enter a valid quantity."
                    );

                    return;
                }


                const amount =
                    product.price * quantity;


                payButton.disabled = true;
                payButton.innerText =
                    "Creating order...";


                /*
                    IMPORTANT:

                    product.price is already stored
                    in paise.

                    Therefore DO NOT multiply
                    by 100 here.
                */

                const orderData =
                    await getJSON(
                        "/order",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                amount: amount,
                                product_id: Number(productId),
                                quantity: quantity
                            })
                        }
                    );


                const keyData =
                    await getJSON(
                        "/razorpay-key"
                    );


                if (
                    typeof Razorpay === "undefined"
                ) {

                    throw new Error(
                        "Razorpay Checkout is not loaded."
                    );
                }


                const options = {

                    key: keyData.key_id,

                    amount:
                        orderData.amount,

                    currency:
                        orderData.currency,

                    order_id:
                        orderData.id,

                    name:
                        "MarginMind",

                    description:
                        product.name,


                    handler:
                        async function (paymentResponse) {

                            try {

                                const data =
                                    await getJSON(
                                        "/verify-payment",
                                        {
                                            method: "POST",

                                            headers: {
                                                "Content-Type":
                                                    "application/json"
                                            },

                                            body:
                                                JSON.stringify(
                                                    paymentResponse
                                                )
                                        }
                                    );


                                alert(
                                    data.Message ||
                                    "Payment verified successfully!"
                                );


                                loadDashboardSummary();

                            } catch (error) {

                                console.error(
                                    "Payment verification error:",
                                    error
                                );

                                alert(
                                    error.message ||
                                    "Payment verification failed."
                                );
                            }
                        }
                };


                const razorpay =
                    new Razorpay(options);


                razorpay.open();


                razorpay.on(
                    "payment.failed",
                    function (response) {

                        console.error(
                            "Payment failed:",
                            response
                        );

                        alert(
                            "Payment failed. Please try again."
                        );
                    }
                );


            } catch (error) {

                console.error(
                    "Checkout error:",
                    error
                );

                alert(
                    error.message ||
                    "Unable to create payment order."
                );

            } finally {

                payButton.disabled = false;

                payButton.innerText =
                    "Pay with Razorpay";
            }
        }
    );
}


/* =========================================================
   RECOMMENDATIONS
========================================================= */

async function loadRecommendations() {

    const container =
        document.getElementById(
            "recommendations"
        );

    if (!container) {
        return;
    }


    container.innerHTML =
        "<p>Loading recommendations...</p>";


    try {

        const recommendations =
            await getJSON(
                "/recommendations"
            );


        container.innerHTML = "";


        if (
            !Array.isArray(recommendations) ||
            recommendations.length === 0
        ) {

            container.innerHTML =
                "<p>No pending recommendations.</p>";

            return;
        }


        recommendations.forEach(
            recommendation => {

                const currentPrice =
                    recommendation.current_price / 100;

                const suggestedPrice =
                    recommendation.suggested_price / 100;


                const card =
                    document.createElement("div");

                card.className =
                    "recommendation-card";


                card.innerHTML = `

                    <h3>
                        🧠 AI Pricing Recommendation
                    </h3>

                    <p>
                        <b>Product ID:</b>
                        ${recommendation.product_id}
                    </p>

                    <p class="recommendation-action">
                        <b>Action:</b>
                        ${recommendation.action}
                    </p>

                    <p class="recommendation-price">
                        <b>Price:</b>
                        ₹${currentPrice.toFixed(2)}
                        →
                        ₹${suggestedPrice.toFixed(2)}
                    </p>

                    <p>
                        <b>Reason:</b>
                        ${recommendation.reason}
                    </p>

                    <div class="actions">

                        <button
                            onclick="approveRecommendation(
                                ${recommendation.id}
                            )"
                        >
                            Approve
                        </button>

                        <button
                            onclick="rejectRecommendation(
                                ${recommendation.id}
                            )"
                        >
                            Reject
                        </button>

                    </div>
                `;


                container.appendChild(card);
            }
        );

    } catch (error) {

        console.error(
            "Recommendation error:",
            error
        );

        container.innerHTML =
            `<p>Unable to load recommendations.</p>`;
    }
}


async function approveRecommendation(id) {

    try {

        const data =
            await getJSON(
                `/price change approval?recommendation_id=${id}`,
                {
                    method: "POST"
                }
            );


        alert(
            data.message ||
            "Recommendation approved!"
        );


        await loadRecommendations();

        await loadDashboardSummary();

    } catch (error) {

        console.error(
            "Approval error:",
            error
        );

        alert(
            error.message ||
            "Approval failed."
        );
    }
}


async function rejectRecommendation(id) {

    try {

        const data =
            await getJSON(
                `/reject recommendation?recommendation_id=${id}`,
                {
                    method: "POST"
                }
            );


        alert(
            data.message ||
            "Recommendation rejected!"
        );


        await loadRecommendations();

    } catch (error) {

        console.error(
            "Rejection error:",
            error
        );

        alert(
            error.message ||
            "Rejection failed."
        );
    }
}


/* =========================================================
   AUDIT LOGS
========================================================= */

async function loadAuditLogs() {

    const container =
        document.getElementById("audit");

    if (!container) {
        return;
    }


    container.innerHTML =
        "<p>Loading audit logs...</p>";


    try {

        const logs =
            await getJSON(
                "/audit logs"
            );


        container.innerHTML = "";


        if (
            !Array.isArray(logs) ||
            logs.length === 0
        ) {

            container.innerHTML =
                "<p>No audit logs found.</p>";

            return;
        }


        logs.forEach(log => {

            const oldPrice =
                log.old_price / 100;

            const newPrice =
                log.new_price / 100;


            let statusText =
                log.status;


            if (log.status === "success") {

                statusText =
                    "✅ SUCCESS";

            } else if (
                log.status === "rejected"
            ) {

                statusText =
                    "❌ REJECTED";

            } else if (
                log.status === "blocked"
            ) {

                statusText =
                    "⚠️ BLOCKED";
            }


            const card =
                document.createElement("div");

            card.className =
                "audit-card";


            card.innerHTML = `

                <h3>
                    📋 Product ${log.product_id}
                </h3>

                <p>
                    <b>Action:</b>
                    ${log.action}
                </p>

                <p>
                    <b>Price:</b>
                    ₹${oldPrice.toFixed(2)}
                    →
                    ₹${newPrice.toFixed(2)}
                </p>

                <p class="audit-status">
                    <b>Status:</b>
                    ${statusText}
                </p>

                <p>
                    <b>Reason:</b>
                    ${log.reason}
                </p>

            `;


            container.appendChild(card);
        });

    } catch (error) {

        console.error(
            "Audit log error:",
            error
        );

        container.innerHTML =
            "<p>Unable to load audit logs.</p>";
    }
}


/* =========================================================
   CHATBOT MARKDOWN FORMATTER
========================================================= */

function escapeHTML(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


function formatAIResponse(text) {

    if (!text) {
        return "";
    }


    let html =
        escapeHTML(text);


    // Headings
    html =
        html.replace(
            /^### (.*)$/gm,
            "<h3>$1</h3>"
        );

    html =
        html.replace(
            /^## (.*)$/gm,
            "<h2>$1</h2>"
        );

    html =
        html.replace(
            /^# (.*)$/gm,
            "<h1>$1</h1>"
        );


    // Bold
    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    // Bullet points
    html =
        html.replace(
            /^\s*[-*] (.*)$/gm,
            "<li>$1</li>"
        );


    // Numbered points
    html =
        html.replace(
            /^\s*\d+\.\s+(.*)$/gm,
            "<li>$1</li>"
        );


    // Group consecutive list items
    html =
        html.replace(
            /(<li>.*?<\/li>\n?)+/gs,
            match => `<ul>${match}</ul>`
        );


    // Horizontal markdown line
    html =
        html.replace(
            /^---$/gm,
            "<hr>"
        );


    // Preserve line breaks
    html =
        html.replace(
            /\n\n/g,
            "<br><br>"
        );

    html =
        html.replace(
            /\n/g,
            "<br>"
        );


    return html;
}


/* =========================================================
   CHATBOT
========================================================= */

function initChatbot() {

    const chatForm =
        document.getElementById("chatForm");

    const chatInput =
        document.getElementById("chatInput");

    const chatMessages =
        document.getElementById("chatMessages");


    // Not chatbot page
    if (
        !chatForm ||
        !chatInput ||
        !chatMessages
    ) {
        return;
    }


    chatForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();


            const message =
                chatInput.value.trim();


            if (!message) {
                return;
            }


            /* USER MESSAGE */

            const userMessage =
                document.createElement("div");

            userMessage.className =
                "user-message chat-message";


            userMessage.innerHTML = `
                <b>You:</b>
                <div>${escapeHTML(message)}</div>
            `;


            chatMessages.appendChild(
                userMessage
            );


            chatInput.value = "";

            chatInput.disabled = true;


            /* BOT MESSAGE */

            const botMessage =
                document.createElement("div");

            botMessage.className =
                "bot-message chat-message";


            botMessage.innerHTML = `
                <b>MarginMind:</b>
                <div>Thinking...</div>
            `;


            chatMessages.appendChild(
                botMessage
            );


            chatMessages.scrollTop =
                chatMessages.scrollHeight;


            try {

                const data =
                    await getJSON(
                        "/chat",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                message: message
                            })
                        }
                    );


                botMessage.innerHTML = `
                    <b>MarginMind:</b>
                    <div class="ai-response">
                        ${formatAIResponse(
                            data.response
                        )}
                    </div>
                `;


            } catch (error) {

                console.error(
                    "Chat error:",
                    error
                );


                botMessage.innerHTML = `
                    <b>MarginMind:</b>
                    <div>
                        ${escapeHTML(
                            error.message ||
                            "Unable to connect to the server."
                        )}
                    </div>
                `;
            }


            chatInput.disabled = false;

            chatInput.focus();


            chatMessages.scrollTop =
                chatMessages.scrollHeight;
        }
    );
}


/* =========================================================
   PAGE INITIALIZATION
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadDashboardSummary();

        loadProducts();

        initializeCheckout();

        loadRecommendations();

        loadAuditLogs();

        initChatbot();

    }
);