// Dit is de backend van de Theorio Vragenbeheer Systeem
// Omdat de focus vooral op de frontend ligt, heb ik hier weinig documentatie voor, en is het niet heel mooi geschreven.
// Met de relevante functies.

var getAllSubjects = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    // Only allow GET requests
    if (request.method !== 'GET') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only GET requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key against allowed keys in Firestore
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Fetch subjects with pagination
        const pageSize = Math.min(parseInt(request.query.pageSize) || 50, 100);
        const pageToken = request.query.pageToken;

        let query = admin.firestore()
            .collection('subjects')
            .orderBy('title')
            .limit(pageSize);

        if (pageToken) {
            const lastDoc = await admin.firestore()
                .collection('subjects')
                .doc(pageToken)
                .get();
            if (lastDoc.exists) {
                query = query.startAfter(lastDoc);
            }
        }

        const subjectsSnapshot = await query.get();
        const subjects = [];
        let lastVisible = null;

        // Fetch all questions for all subjects
        for (const doc of subjectsSnapshot.docs) {
            const data = doc.data();
            const questionIds = (data.questionIds || []).slice(0, 1000);
            
            // Fetch questions for this subject
            const questions = [];
            if (questionIds.length > 0) {
                const questionsSnapshot = await admin.firestore()
                    .collection('questions')
                    .where(admin.firestore.FieldPath.documentId(), 'in', questionIds)
                    .get();

                questionsSnapshot.forEach(questionDoc => {
                    questions.push({
                        id: questionDoc.id,
                        ...questionDoc.data()
                    });
                });
            }

            subjects.push({
                id: doc.id,
                title: data.title,
                questionIds: questionIds, // Keep original IDs
                questions: questions // Add the actual question data
            });
            
            lastVisible = doc;
        }

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'getAllSubjects');

        response.status(200).send({
            subjects,
            pagination: {
                nextPageToken: lastVisible ? lastVisible.id : null,
                pageSize,
                hasMore: subjects.length === pageSize
            }
        });

    } catch (error) {
        console.error('Error in getAllSubjects:', error);
        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het ophalen van de onderwerpen en vragen, probeer het later opnieuw.'
        });
    }
});

var getAllExams = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    if (request.method !== 'GET') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only GET requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Fetch all exam documents
        const examsSnapshot = await admin.firestore()
            .collection('exams')
            .get();

        const exams = [];

        // Process each exam document
        for (const examDoc of examsSnapshot.docs) {
            const examData = examDoc.data();
            const examResult = {
                id: examDoc.id,
                gevaarherkenning: { questionIds: [], questions: [] },
                inzicht: { questionIds: [], questions: [] },
                kennis: { questionIds: [], questions: [] }
            };

            // Process each exam type
            for (const examType of ['gevaarherkenning', 'inzicht', 'kennis']) {
                // Ensure questionIds is an array and contains only valid strings
                const questionIds = Array.isArray(examData[examType]) 
                    ? examData[examType].filter(id => typeof id === 'string' && id.length > 0)
                    : [];
                
                examResult[examType].questionIds = questionIds;

                // Fetch questions in batches of 10
                if (questionIds.length > 0) {
                    for (let i = 0; i < questionIds.length; i += 10) {
                        const batch = questionIds.slice(i, i + 10);
                        const questions = await Promise.all(
                            batch.map(async (qId) => {
                                try {
                                    const questionDoc = await admin.firestore()
                                        .collection('questions')
                                        .doc(qId)
                                        .get();
                                    
                                    if (questionDoc.exists) {
                                        return {
                                            id: questionDoc.id,
                                            ...questionDoc.data()
                                        };
                                    }
                                    console.warn(`Question ${qId} not found`);
                                    return null;
                                } catch (error) {
                                    console.error(`Error fetching question ${qId}:`, error);
                                    return null;
                                }
                            })
                        );

                        // Filter out any null values (non-existent questions)
                        const validQuestions = questions.filter(q => q !== null);
                        examResult[examType].questions.push(...validQuestions);
                    }
                }
            }

            exams.push(examResult);
        }

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'getAllExams');

        response.status(200).send({
            exams: exams
        });

    } catch (error) {
        console.error('Error in getAllExams:', error);
        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het ophalen van de examens en vragen, probeer het later opnieuw.'
        });
    }
});

var updateQuestion = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    // Only allow PUT requests
    if (request.method !== 'PUT') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only PUT requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key against allowed keys in Firestore
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Validate request body
        const question_data = request.body;
        if (!question_data || !question_data.id) {
            response.status(400).send({
                error: 'Bad Request',
                message: 'Question data and ID are required'
            });
            return;
        }

        // Update the question document
        await admin.firestore()
            .collection('questions')
            .doc(question_data.id)
            .update({
                ...question_data,
                updatedAt: admin.firestore.FieldValue.serverTimestamp()
            });

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'updateQuestion');

        response.status(200).send({
            status: 'success',
            message: 'Question updated successfully',
            questionId: question_data.id
        });

    } catch (error) {
        console.error('Error in updateQuestion:', error);
        
        // Handle specific Firestore errors
        if (error.code === 'not-found') {
            response.status(404).send({
                error: 'Not Found',
                message: 'Question not found'
            });
            return;
        }

        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het bijwerken van de vraag, probeer het later opnieuw.'
        });
    }
});

var deleteQuestion = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    // Only allow DELETE requests
    if (request.method !== 'DELETE') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only DELETE requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key against allowed keys in Firestore
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Get question ID from query parameters
        const questionId = request.query.id;
        if (!questionId) {
            response.status(400).send({
                error: 'Bad Request',
                message: 'Question ID is required'
            });
            return;
        }

        // Check if question exists before deleting
        const questionRef = admin.firestore().collection('questions').doc(questionId);
        const questionDoc = await questionRef.get();

        if (!questionDoc.exists) {
            response.status(404).send({
                error: 'Not Found',
                message: 'Question not found'
            });
            return;
        }

        // Delete the question document
        await questionRef.delete();

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'deleteQuestion');

        response.status(200).send({
            status: 'success',
            message: 'Question deleted successfully',
            questionId: questionId
        });

    } catch (error) {
        console.error('Error in deleteQuestion:', error);
        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het verwijderen van de vraag, probeer het later opnieuw.'
        });
    }
});

var createQuestion = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    // Only allow POST requests
    if (request.method !== 'POST') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only POST requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key against allowed keys in Firestore
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Validate request body and required fields
        const questionData = request.body;
        if (!questionData || typeof questionData !== 'object') {
            response.status(400).send({
                error: 'Bad Request',
                message: 'Question data is required'
            });
            return;
        }

        // Required fields validation
        const requiredFields = ['question', 'type', 'parent'];
        const missingFields = requiredFields.filter(field => !questionData[field]);
        
        if (missingFields.length > 0) {
            response.status(400).send({
                error: 'Bad Request',
                message: `Missing required fields: ${missingFields.join(', ')}`
            });
            return;
        }

        // Create new question document
        const newQuestionRef = admin.firestore().collection('questions').doc();
        const questionId = newQuestionRef.id;
        
        // Prepare question data
        const finalQuestionData = {
            ...questionData,
            id: questionId,
            createdAt: admin.firestore.FieldValue.serverTimestamp(),
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
        };

        // Create the question document
        await newQuestionRef.set(finalQuestionData);

        // Handle parent relationship
        if (questionData.parent.includes('Examen')) {
            // Extract exam number from parent string
            const examNumber = questionData.parent.match(/\d+/)[0];
            const examRef = admin.firestore().collection('exams').doc(examNumber);

            // Determine the correct array to update based on the exam type
            let arrayField;
            if (questionData.parent.includes('Gevaarherkenning')) {
                arrayField = 'gevaarherkenning';
            } else if (questionData.parent.includes('Inzicht')) {
                arrayField = 'inzicht';
            } else if (questionData.parent.includes('Kennis')) {
                arrayField = 'kennis';
            } else {
                response.status(400).send({ 
                    error: 'Bad Request',
                    message: "Invalid exam type. Must include 'Gevaarherkenning', 'Inzicht', or 'Kennis'" 
                });
                return;
            }

            // Update the exam document with the new question ID
            const updateData = {};
            updateData[arrayField] = admin.firestore.FieldValue.arrayUnion(questionId);
            await examRef.update(updateData);
        } else {
            // Handle subject relationship
            const subjectQuery = await admin.firestore()
                .collection('subjects')
                .where('title', '==', questionData.parent)
                .get();
            
            if (subjectQuery.empty) {
                response.status(404).send({ 
                    error: 'Not Found',
                    message: `Subject with title '${questionData.parent}' not found` 
                });
                return;
            }

            // Update the subject document with the new question ID
            const subjectDoc = subjectQuery.docs[0];
            await subjectDoc.ref.update({
                questionIds: admin.firestore.FieldValue.arrayUnion(questionId)
            });
        }

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'createQuestion');

        response.status(201).send({
            status: 'success',
            message: 'Question created successfully',
            questionId: questionId,
            question: finalQuestionData
        });

    } catch (error) {
        console.error('Error in createQuestion:', error);
        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het aanmaken van de vraag, probeer het later opnieuw.'
        });
    }
});

var getAllFeedback = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    // Only allow GET requests
    if (request.method !== 'GET') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only GET requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key against allowed keys in Firestore
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Fetch feedback with pagination
        const pageSize = Math.min(parseInt(request.query.pageSize) || 50, 100);
        const pageToken = request.query.pageToken;
        const status = request.query.status; // Optional status filter

        let query = admin.firestore()
            .collection('feedback')
            .orderBy('date', 'desc'); // Order by date, newest first

        // Add status filter if provided
        if (status) {
            query = query.where('status', '==', status);
        }

        query = query.limit(pageSize);

        if (pageToken) {
            const lastDoc = await admin.firestore()
                .collection('feedback')
                .doc(pageToken)
                .get();
            if (lastDoc.exists) {
                query = query.startAfter(lastDoc);
            }
        }

        const feedbackSnapshot = await query.get();
        const feedbackItems = [];
        let lastVisible = null;

        for (const doc of feedbackSnapshot.docs) {
            const data = doc.data();
            
            feedbackItems.push({
                id: doc.id,
                subject: data.subject,
                feedback: data.feedback,
                date: data.date,
                status: data.status,
                questionId: data.questionId,
                userId: data.userId
            });
            
            lastVisible = doc;
        }

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'getAllFeedback');

        response.status(200).send({
            feedback: feedbackItems,
            pagination: {
                nextPageToken: lastVisible ? lastVisible.id : null,
                pageSize,
                hasMore: feedbackItems.length === pageSize
            }
        });

    } catch (error) {
        console.error('Error in getAllFeedback:', error);
        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het ophalen van de feedback, probeer het later opnieuw.'
        });
    }
});

var updateFeedbackStatus = onRequest({ 
    region: "europe-west1",
    maxInstances: 10,
    timeoutSeconds: 30,
    memory: '256MiB',
    cors: true 
}, async (request, response) => {
    // Only allow PUT requests
    if (request.method !== 'PUT') {
        response.status(405).send({
            error: 'Method not allowed',
            message: 'Only PUT requests are allowed'
        });
        return;
    }

    try {
        // API Key validation
        const apiKey = request.headers['x-api-key'];
        if (!apiKey) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Missing API key'
            });
            return;
        }

        // Validate API key against allowed keys in Firestore
        const apiKeyDoc = await admin.firestore()
            .collection('api_keys')
            .doc(apiKey)
            .get();

        if (!apiKeyDoc.exists || !apiKeyDoc.data().active) {
            response.status(401).send({
                error: 'Unauthorized',
                message: 'Invalid or inactive API key'
            });
            return;
        }

        // Rate limiting check
        const clientIP = request.ip;
        const rateLimit = await checkRateLimit(clientIP, apiKey);
        if (!rateLimit.allowed) {
            response.status(429).send({
                error: 'Too Many Requests',
                message: 'Rate limit exceeded',
                retryAfter: rateLimit.retryAfter
            });
            return;
        }

        // Validate request body
        const { feedbackId, status } = request.body;
        if (!feedbackId || !status) {
            response.status(400).send({
                error: 'Bad Request',
                message: 'Feedback ID and status are required'
            });
            return;
        }

        // Update the feedback document
        await admin.firestore()
            .collection('feedback')
            .doc(feedbackId)
            .update({
                status,
                updatedAt: admin.firestore.FieldValue.serverTimestamp()
            });

        // Log the access
        await logAPIAccess(apiKey, clientIP, 'updateFeedbackStatus');

        response.status(200).send({
            status: 'success',
            message: 'Feedback status updated successfully',
            feedbackId: feedbackId
        });

    } catch (error) {
        console.error('Error in updateFeedbackStatus:', error);
        response.status(500).send({
            error: 'Internal Server Error',
            message: 'Een fout is opgetreden bij het bijwerken van de feedback status, probeer het later opnieuw.'
        });
    }
});

exports.http = {
    "getAllSubjects": getAllSubjects,
    "getAllExams": getAllExams,
    "updateQuestion": updateQuestion,
    "deleteQuestion": deleteQuestion,
    "createQuestion": createQuestion,
    "getAllFeedback": getAllFeedback,
    "updateFeedbackStatus": updateFeedbackStatus,
}