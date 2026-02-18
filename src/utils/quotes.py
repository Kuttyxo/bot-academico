
import random

QUOTES = [
    "🚀 'El éxito es la suma de pequeños esfuerzos repetidos día tras día.' - Robert Collier",
    "💡 'La educación es el pasaporte hacia el futuro, el mañana pertenece a aquellos que se preparan para él en el día de hoy.' - Malcolm X",
    "📚 'Cree en ti mismo y en lo que eres. Sé consciente de que hay algo en tu interior que es más grande que cualquier obstáculo.' - Christian D. Larson",
    "🔥 'No cuentes los días, haz que los días cuenten.' - Muhammad Ali",
    "🌟 'La disciplina es el puente entre metas y logros.' - Jim Rohn",
    "🎯 'El único modo de hacer un gran trabajo es amar lo que haces.' - Steve Jobs",
    "📖 'Aprender es como remar contra corriente: en cuanto se deja, se retrocede.' - Edward Benjamin Britten",
    "💪 'La motivación es lo que te pone en marcha. El hábito es lo que hace que sigas.' - Jim Ryun",
    "🌱 'No te preocupes por los fracasos, preocúpate por las oportunidades que pierdes cuando ni siquiera lo intentas.' - Jack Canfield",
    "🧠 'La mente es como un paracaídas, solo funciona si se abre.' - Albert Einstein"
]

def get_random_quote():
    """Returns a random motivational quote."""
    return random.choice(QUOTES)
