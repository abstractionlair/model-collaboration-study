-- Protocol IR — Haskell version
--
-- This is the same typed AST and the same protocols (CCR and ReConcile)
-- that live in src/ir/ and src/protocols/, written in Haskell for direct
-- comparison.
--
-- This file is illustrative — it's not part of the build. The point is to
-- see what the same ideas look like in a language designed for typed
-- functional ASTs, so we can decide whether to switch.
--
-- To actually compile/check this would need GHC. The syntax assumes
-- modern extensions: GADTs, DataKinds, KindSignatures, LambdaCase.

{-# LANGUAGE GADTs            #-}
{-# LANGUAGE DataKinds        #-}
{-# LANGUAGE KindSignatures   #-}
{-# LANGUAGE LambdaCase       #-}

module ProtocolIR where

-- ============================================================================
-- Stage tags (lifted to the type level via DataKinds)
-- ============================================================================

data Stage = Draft | Final | Plan

-- ============================================================================
-- Annotation enums
-- ============================================================================

data ContextMode = Fresh | Accumulated
  deriving (Show, Eq)

data Visibility
  = ArtifactOnly
  | WithProduction
  | PeersGrouped
  | All
  deriving (Show, Eq)

-- ============================================================================
-- Semantic value types
-- ============================================================================

type Model = String

data Query
data Answer (s :: Stage)
data Critique a
data Score a

-- ============================================================================
-- Typed AST
-- ============================================================================

data Expr a where
  -- Leaves
  QueryVar :: String -> Expr Query

  -- Single-model generation and review
  Gen      :: Model -> Expr Query -> Expr (Answer 'Draft)
  Review   :: Model
           -> Expr (Answer 'Draft)
           -> ContextMode
           -> Visibility
           -> Expr (Critique (Answer 'Draft))
  Revise   :: Model
           -> Expr (Answer 'Draft)
           -> Expr (Critique (Answer 'Draft))
           -> Expr (Answer 'Draft)
  Finalize :: Expr (Answer 'Draft) -> Expr (Answer 'Final)

  -- Parallel operations across models
  ParGen      :: [Model]
              -> Expr Query
              -> Expr [Answer 'Draft]
  ReviseRound :: [Model]
              -> Expr [Answer 'Draft]
              -> ContextMode
              -> Visibility
              -> Expr [Answer 'Draft]
  Rounds      :: Int
              -> [Model]
              -> Expr [Answer 'Draft]
              -> ContextMode
              -> Visibility
              -> Expr [Answer 'Draft]
  ParScore    :: [Model]
              -> Expr [Answer 'Draft]
              -> Expr [Score (Answer 'Draft)]

  -- Aggregation
  WeightedVote :: Expr [Answer 'Draft]
               -> Expr [Score (Answer 'Draft)]
               -> Expr (Answer 'Draft)

  -- Let binding via HOAS — the body is a Haskell function.
  -- The type of the bound variable is inferred from the value's type.
  Let :: Expr a -> (Expr a -> Expr b) -> Expr b


-- ============================================================================
-- Protocols
-- ============================================================================

-- Cross-Context Review
ccr :: Model -> Expr (Answer 'Final)
ccr m =
  let q     = QueryVar "q"
      d     = Gen m q
      f     = Review m d Fresh ArtifactOnly
      d'    = Revise m d f
  in Finalize d'

-- Same-Session Review (baseline)
sr :: Model -> Expr (Answer 'Final)
sr m =
  let q  = QueryVar "q"
      d  = Gen m q
      f  = Review m d Accumulated All
      d' = Revise m d f
  in Finalize d'

-- Subagent Review (baseline)
sa :: Model -> Expr (Answer 'Final)
sa m =
  let q  = QueryVar "q"
      d  = Gen m q
      f  = Review m d Fresh WithProduction
      d' = Revise m d f
  in Finalize d'


-- ReConcile
reconcile :: [Model] -> Int -> Expr (Answer 'Final)
reconcile models rounds =
  let q       = QueryVar "q"
      initial = ParGen models q
      refined = Rounds rounds models initial Fresh PeersGrouped
  in Let refined $ \r ->
       Finalize (WeightedVote r (ParScore models r))


-- ReConcile ablation: zero discussion rounds
reconcileNoDiscussion :: [Model] -> Expr (Answer 'Final)
reconcileNoDiscussion models = reconcile models 0


-- ============================================================================
-- Pretty-printer interpreter
-- ============================================================================

describe :: Expr a -> String
describe = go 0
  where
    pad n = replicate (n * 2) ' '

    go :: Int -> Expr a -> String
    go n e = pad n ++ case e of
      QueryVar v ->
        v ++ " : Query"
      Gen m q ->
        "Gen(" ++ m ++ ") : Query -> Answer Draft\n" ++ go (n+1) q
      Review m t c v ->
        "Review(" ++ m ++ ", " ++ show c ++ ", " ++ show v ++ ") : ...\n"
        ++ go (n+1) t
      Revise m d f ->
        "Revise(" ++ m ++ ") : Answer Draft x Critique -> Answer Draft\n"
        ++ go (n+1) d ++ "\n" ++ go (n+1) f
      Finalize d ->
        "Finalize : Answer Draft -> Answer Final\n" ++ go (n+1) d
      ParGen ms q ->
        "ParGen(" ++ show ms ++ ") : Query -> [Answer Draft]\n" ++ go (n+1) q
      ReviseRound ms ds c v ->
        "ReviseRound(" ++ show ms ++ ") : ...\n" ++ go (n+1) ds
      Rounds k ms ds c v ->
        "Rounds(n=" ++ show k ++ ", " ++ show ms ++ ") : ...\n" ++ go (n+1) ds
      ParScore ms ds ->
        "ParScore(" ++ show ms ++ ") : ...\n" ++ go (n+1) ds
      WeightedVote ds ss ->
        "WeightedVote : ...\n" ++ go (n+1) ds ++ "\n" ++ go (n+1) ss
      Let val body ->
        let placeholder = QueryVar "<bound>"  -- hack for traversal
        in "let _v = ...\n" ++ go (n+1) val
           ++ "\n" ++ pad n ++ "in ...\n"
        -- Real traversal of HOAS bodies needs a slightly more careful
        -- machinery (see "Boxes Go Bananas" / circular traversal). The
        -- short version: substitute a tagged Var, walk the result.
