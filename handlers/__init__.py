from .message_handler import router as message_router
# from .callback_handler import router as callback_router
from .agreement_handler import router as agreement_router
# from .questions_handlers.question_flow_handler import router as question_router
from .subscribtion_handler import router as subscribtion_router
from .photo_handler import router as photo_router 
from .requisites_handler import router as requisites_router
from .unexpected_text_handler import router as unexpected_text_router


from .questions_handlers.question_product_ordered_handler import router as order_router
from .questions_handlers.questiong_order_receive_handler import router as receive_order_router
from .questions_handlers.question_feedback_done_handler import router as feedback_router
from .questions_handlers.question_shk_handler import router as shk_router