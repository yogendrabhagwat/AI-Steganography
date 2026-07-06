const Steganography = {
    encode: async function (imageFile, message, password) {
        if (!password) {
            throw new Error("Password is required for Secure AI Encoding.");
        }
        const formData = new FormData();
        formData.append('cover_image', imageFile);
        formData.append('secret_text', message);
        formData.append('password', password);

        const response = await fetch('/api/encode', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to encode data');
        }

        const resJson = await response.json();
        return resJson;
    },

    decode: async function (imageFile, password) {
        if (!password) {
            throw new Error("Password is required for Secure AI Decoding.");
        }
        const formData = new FormData();
        formData.append('stego_image', imageFile);
        formData.append('password', password);

        const response = await fetch('/api/decode', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to decode data');
        }

        const resJson = await response.json();
        return resJson.extracted_data.content;
    }
};

window.Steganography = Steganography;