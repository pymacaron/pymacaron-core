def return_token(*args):
    return http_reply({'token': '123123123'}, 200)

# Dummy implementation of model persistence
class PersistentFoo():

    @staticmethod
    def load_from_db(*args, **kwargs):
        # Load object(s) from storage
        pass

    @staticmethod
    def save_to_db(object, *args, **kwargs):
        # Put object into storage
        pass
